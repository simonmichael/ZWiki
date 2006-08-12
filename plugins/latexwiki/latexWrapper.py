### ###
###

import os, sys, re, zLOG, string, math
from util import fileNameFor, imageExtension, unique, workingDir, runCommand, log, findinpath
from PIL import Image, ImageFile, ImageChops, PngImagePlugin
from cgi import escape

class LatexSyntaxError(Exception): pass
class LatexRenderError(Exception): pass
class GhostscriptError(Exception): pass
class AlignError(Exception): pass

# find our external programs
dvipngpath = findinpath('dvipng')
gspath     = findinpath('gs')
latexpath  = findinpath('latex')
dvipspath  = findinpath('dvips')

charsizept = 10
# dvipng and tex use 72.27 points per inch, internally and thus generate the
# best-looking images.  Postscript uses 72 points per inch.  So if we have to
# use ghostscript and go through a postscript conversion, there is a resolution
# mismatch which puts nibs on the tops of letters for many choices of
# charheightpx.
if dvipngpath is not None:
    ptperinch = 72.27
else:
    ptperinch = 72
# Adjust the centerline by this many pixels, key is character height in px
# This list was determined experimentally.  If anyone has a better algorithm
# to align images, please contact me.
centerfudge = dict({ # positive to move up, negative to move down
    10:0,  11:+1, 12:0,  13:0,  14:0,  15:+2, 16:0, 17:0,  18:0,  19:0,  20:0,
    21:0,  22:0,  23:+2, 24:0,  25:0,  26:0,  27:0, 28:0,  29:0,  30:0,  31:+1,
    32:0,  33:+1, 34:0,  35:0,  36:0,  37:0,  38:0, 39:+1, 40:0,  41:+1, 42:-1,
    43:0,  44:0,  45:0,  46:0,  47:+1, 48:0,  49:0, 50:0,  51:0,  52:-1, 53:0,
    54:-1, 55:+1, 56:-1, 57:+1, 58:+3, 59:-1, 60:0, 61:-1, 62:-1, 63:+1, 64:-1 
    })

latexInlinePattern = r'^(\$(?!\$)|\\\()$'

# This is only used if your wiki does not have a node LatexTemplate.
defaultLatexTemplate = r"""
\documentclass[%dpt,notitlepage]{article}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage[all]{xy}
\newenvironment{latex}{}{}
\oddsidemargin -86pt
\headheight 0pt
\topmargin -96pt
\nofiles
\begin{document}
\pagestyle{empty}
%%s
\end{document}
"""  % (charsizept)

def imageDoesNotExist(code, charheightpx):
    return not os.path.exists(os.path.join(workingDir, 
        fileNameFor(code, charheightpx, imageExtension)))

def renderNonexistingImages(latexCodeList, charheightpx, alignfudge, resfudge, **kw):
    """ take a list of strings of latex code, render the
    images that don't already exist.
    """
    latexTemplate = (kw.get('latexTemplate', defaultLatexTemplate) or
                     defaultLatexTemplate)
    m = re.search(r'\\documentclass\[[^\]]*?(\d+)pt[^\]]*?\]', \
        latexTemplate)
    if m:
        charsizept = int(m.group(1))
    else:
        charsizept = 10
    res = charheightpx*ptperinch/charsizept*resfudge
    errors = ""
    codeToRender = filter(lambda x: imageDoesNotExist(x, charheightpx), unique(latexCodeList))
    if (not codeToRender): return
    unifiedCode = re.sub(r'^(\$|\\\()', r'\1|~ ', codeToRender[0])
    for code in codeToRender[1:len(codeToRender)]:
        unifiedCode = unifiedCode + '\n\\newpage\n' + re.sub(r'^(\$|\\\()', r'\1|~ ', code)
    try:
       runLatex(unifiedCode, res, charheightpx, latexTemplate)
    except LatexSyntaxError, data:
       errors = str(data)
       log(errors, 'LatexSyntaxError')
       # FIXME translate latex line number to source line number
       return escape(errors)

    fName = fileNameFor(unifiedCode, charheightpx)
    dviPng(fName, res)
    for code, i in map(None, codeToRender, range(0, len(codeToRender))):
        newFileName = fileNameFor(code, charheightpx, imageExtension)
        imname = '%s-%03d.png'%(fName,i+1)
        if re.match(r'^(?:\$|\\\()', code): # FIXME make dvipng do the alpha properly
            im = Image.open(os.path.join(workingDir, imname))
            try:
                im = align(im, charheightpx, alignfudge) # returns an RGBA image
            except (AlignError, ValueError), data:
                raise LatexRenderError(str(data) + '\nThe code was:\n' + \
                    code+ '\nin the file %s'%(os.path.join(workingDir, imname)))
            if im.mode != 'RGBA':
                alpha = ImageChops.invert(im.convert('L'))
                im = im.putalpha(alpha)
            im.save(os.path.join(workingDir, newFileName), "PNG")
        else:
            os.rename(os.path.join(workingDir, imname), os.path.join(workingDir, newFileName))
    os.system('cd %s; rm -f *.log *.aux *.tex *.pdf *.dvi *.ps %s-???.png'%(workingDir, fName))
    return escape(errors)

def runLatex(code, res, charheightpx, latexTemplate):
    def ensureWorkingDirectory(path):
        """Ensure this directory exists and is writable."""
        if not os.access(path,os.F_OK): os.mkdir(path)
        if not os.access(path,os.W_OK): os.system('chmod u+rwx %s' % path)

    texfileName = fileNameFor(code, charheightpx, '.tex')
    dvifileName = fileNameFor(code, charheightpx, '.dvi')
    psfileName = fileNameFor(code, charheightpx, '.ps')
    cmdLine = '%s %s' %(latexpath, texfileName)

    ensureWorkingDirectory(workingDir)
    file = open(os.path.join(workingDir, texfileName), 'w')
    file.write(latexTemplate %(code,))
    file.close()

    err, stdout, stderr = runCommand(cmdLine)
    
    if err:
        out = stderr + '\n' + stdout
        err = re.search('!.*\?', out, re.MULTILINE+re.DOTALL)
        if err:
            out = err.group(0)
# FIXME translate latex line numbers to source line numbers
        raise LatexSyntaxError(out)

def dviPng(fName, res):
    input, output = fName+'.dvi', fName+'-%03d.png'
    gspngfname = fName+'-gs-%03d.png'
    psfname = fName+'-gs'; i=1
    # '--truecolor -bg Transparent' generates RGB images with transparent pixel
    # (not alpha channel) but it's close...
    if dvipngpath is not None:
        cmdLine = '%s --truecolor -bg Transparent -picky -D %f -Ttight -o %s %s'%\
            (dvipngpath, res, output, input)
        err, stdout, stderr = runCommand(cmdLine)
        ppredo = []
        if not err: return
        # dvipng -picky will give the following message on pages it cannot render
        # (usually due to the use of postscript specials).  For that we fall
        # through to ghostscript
        matcher = re.finditer(r'\[(\d+) not rendered\]', stdout)
        for m in matcher:
            if ppredo: ppredo += ','
            ppredo.append(m.group(1))
        ppopt = '-pp ' + string.join(ppredo,',')
    else:
        ppopt = ''
    cmdLine = '%s %s -R -D %f -o %s %s'%(dvipspath, ppopt, res, psfname+'.ps', input)
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n'%(err, stdout, stderr), 'DVIPSError')
        raise DVIPSError(stderr+'\n'+stdout)
    if not ppopt:
        ppredo = range(1,len(re.findall(r'\[\d+\]', stderr))+1)
    err = runGhostscript(psfname, res, 'pngalpha')
    center(psfname, res)
    for page in ppredo:
        oldfname = os.path.join(workingDir, gspngfname%i)
        newfname = os.path.join(workingDir, output%int(page))
        os.rename(oldfname, newfname)
        i += 1

def runGhostscript(fName, res, device):
    input, output = fName+'.ps', fName+'-%03d.png'
    cmdLine = '%s -dDOINTERPOLATE -dTextAlphaBits=4 '%gspath + \
              '-dGraphicsAlphaBits=4 -r%f -sDEVICE=%s ' + \
              '-dBATCH -dNOPAUSE -dQUIT -sOutputFile=%s %s '
    cmdLine = cmdLine %(res, device, output, input)
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n'%(err, stdout, stderr), 'GhostscriptError')
        raise GhostscriptError(stderr+'\n'+stdout)
    return stderr # when using bbox, BoundingBox is on stderr

# assumes png's already created
def center(fName, res):
    bboxes = re.split('\n', runGhostscript(fName, res, 'bbox'))
    pngfname = fName+'-%03d.png'
    for i in range(0, len(bboxes)/2):
        file = pngfname%(i+1)
        start_x, start_y, end_x, end_y = map(float, 
            re.match(r'%%HiResBoundingBox: ([0-9\.]+) ([0-9\.]+) ([0-9\.]+) ([0-9\.]+)', 
                bboxes[2*i+1]).groups())
        xsize = int(round(((end_x - start_x) * res)/ptperinch))
        ysize = int(round(((end_y - start_y) * res)/ptperinch))
        if (xsize <= 0): xsize = 1
        if (ysize <= 0): ysize = 1
        start_x = int(round(start_x*res/ptperinch))
        start_y = int(round(start_y*res/ptperinch))
        im = Image.open(os.path.join(workingDir, file))
        cropdim = (start_x, im.size[1]-start_y-ysize, start_x+xsize, im.size[1]-start_y)
        cropdim = map(int, map(round, cropdim))
        im = im.crop(cropdim)
        im2 = Image.new('RGBA', im.size, (255,255,255))
        im2.paste(im, (0, 0))
        if im.mode != 'RGBA':
            alpha = ImageChops.invert(im2.convert('L'))  # Image should already have an alpha
            im3 = Image.new('RGBA', im.size, (0,0,0))
            im3.putalpha(alpha)
            im2 = im3
        im2.save(os.path.join(workingDir, file), "PNG")

def align(im, charheightpx=0, alignfudge=0):
    dotstartx = -1; dotendx = -1; dotstarty = -1; dotendy = -1
    widentop = 0; widenbottom = 0; letterstartx = -1; chopx = 0
    if im.mode == 'P':
        white = 0
    elif im.mode == 'RGB':
        white = (255,255,255)
    elif im.mode == 'RGBA':
        white = (254,254,254,0) # as output by ghostscript pngalpha device
    elif im.mode == 'L':
        white = 255 # FIXME I think
    for x in range(0,im.size[0]):  # Try to find the leading dot
        if(dotendy < 0) :
            for y in range(0, im.size[1]):
                if(dotstarty >= 0 and dotendy < 0): 
                    if(im.getpixel((x,y)) == white):
                        dotendy = y
                        break
                if(dotstarty < 0 and im.getpixel((x,y)) != white):
                    dotstartx = x
                    dotstarty = y
            else:
                if dotstarty >= 0 and dotendy < 0:
                    dotendy = im.size[1]
        elif(dotendx < 0):
            maybedotendx = x
            for y in range(dotstarty, dotendy):
                if(im.getpixel((x,y)) != white):
                    maybedotendx = -1
            if maybedotendx > 0:
                dotendx = x
        else:
            for y in range(0,im.size[1]):
                if(im.getpixel((x,y)) != white):
                    letterstartx = x
                    break
            if letterstartx>0: break
    else: # failed to find letterstartx
        log('dotstartx=%d, dotendx=%d, dotstarty=%d, dotendy=%d, letterstartx=%d\n'
            %(dotstartx, dotendx, dotstarty, dotendy, letterstartx))
        log('Unable to find dot. (size=%dx%d)\n'%(im.size[0],im.size[1]), 'renderNonExistingImages')
        raise AlignError('Image appears to be blank or not have an alignment dot.')
    centerline = (dotendy-dotstarty)/2.0    # increase centerline to move char up WRT text
    dotcenter = (dotendy-dotstarty)*7.0/144.0
    centerline += dotcenter
    if centerfudge.has_key(charheightpx):
        centerline += centerfudge[charheightpx]/2.0
    # if dot is not pixel-aligned, take that into account
    # sum pixels above and below (dotendy-dotstarty)/2
    dottophalf = 0
    dotlinesize = dotendx-dotstartx
    dottoplines = 0
    for y in range(dotstarty, int(math.ceil(dotstarty+(dotendy-1-dotstarty)/2.0))):
        dottoplines += 1
        for x in range(dotstartx, dotendx):
            dottophalf += cabs(im.getpixel((x,y)))
        break
    else:
        dottophalf = 1 # dot was 1px high
    dotbottomhalf = 0
    for y in range(dotendy-1, dotstarty+(dotendy-1-dotstarty)/2,-1):
        for x in range(dotstartx, dotendx):
            dotbottomhalf += cabs(im.getpixel((x,y)))
        break
    else:
        dotbottomhalf = 1 # dot was 1px high
    if(dottophalf != 0.0 and dotbottomhalf != 0):
        dotpixmiss = float(dottophalf-dotbottomhalf)/(dottophalf+dotbottomhalf)
    else:
        dotpixmiss = 0.0
    centerline += dotpixmiss 
    centerline += alignfudge # user parameter -- FIXME remove?
    bottomsize = im.size[1]-centerline               # pixels below midline
    topsize = centerline                             # pixels above midline
    if(topsize > bottomsize):
        newheight = 2*topsize
        widenbottom = topsize - topsize
    else: 
        newheight = 2*bottomsize
        widentop = bottomsize - topsize
    chopx = letterstartx-1
    newheight= int(newheight)
    widentop = 0 #int(widentop) #SKWM broken
    im2 = Image.new('RGBA', (im.size[0]-chopx,newheight), (255,255,255))
    im2.paste(im,(-chopx,widentop,im.size[0]-chopx,im.size[1]-widentop))
    return im2

def cabs(A):
    sq = 0.0
    if type(A) == type(()):
        for i in range(0,3):
            sq += A[i]*A[i]
        if len(A) == 4:
            return math.sqrt(sq)*(A[3]/255.0)
        else:
            return math.sqrt(sq)
    else:
        return A
