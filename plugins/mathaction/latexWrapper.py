### ###
###

import os, sys, re, popen2, glob, zLOG, select, fcntl, string
from util import fileNameFor, imageExtension, unique, workingDir
from PIL import Image, ImageFile, ImageChops, PngImagePlugin
from cgi import escape

class LatexSyntaxError(Exception): pass
class GhostscriptError(Exception): pass

charsizept = 10
ptperinch = 72.0

# This is only used if your wiki does not have a node LatexTemplate.
defaultLatexTemplate = r"""
\documentclass[%dpt,notitlepage]{article}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage[all]{xy}
\newenvironment{latex}{}{}
\begin{document}
\pagestyle{empty}
%%s
\end{document}
"""  % (charsizept)

def log(message,summary='',severity=0):
        zLOG.LOG('LatexWikiDebugLog',severity,summary,message)

def imageDoesNotExist(code, charheightpx):
    return not os.path.exists(os.path.join(workingDir, 
        fileNameFor(code, charheightpx, imageExtension)))

def renderNonexistingImages(latexCodeList, charheightpx, alignfudge, resfudge, **kw):
    """ take a list of strings of latex code, render the
    images that don't already exist.
    """
    from string import join

    res = int(round(charheightpx*ptperinch/charsizept*resfudge))
    errors = ""
    latexTemplate = (kw.get('latexTemplate', defaultLatexTemplate) or
                     defaultLatexTemplate)
    
    codeToRender = filter(lambda x: imageDoesNotExist(x, charheightpx), unique(latexCodeList))
    
    if (not codeToRender): return

#    unifiedCode = re.sub(r'^(\$|\\\()', r'\1\cdot ', codeToRender[0])
#    for code in codeToRender[1:len(codeToRender)]:
#        unifiedCode = unifiedCode + '\n\\newpage\n' + re.sub(r'^(\$|\\\()', r'\1\cdot ', code)

    unifiedCode = codeToRender[0]
    for code in codeToRender[1:len(codeToRender)]:
        unifiedCode = unifiedCode + '\n\\newpage\n' + code

    try:
       runLatex(unifiedCode, charheightpx, latexTemplate)
    except LatexSyntaxError, data:
       errors = str(data)
       log(errors, 'LatexSyntaxError')
       return escape(errors)

    fName = fileNameFor(unifiedCode, charheightpx)

    # XXX added latexwiki's dvips step
    dvipspath = '/usr/bin/dvips'
    ppopt = ''
    cmdLine = '%s %s -R -D %f -o %s %s'%(dvipspath, ppopt, res, fName+'.ps', fName+'.dvi')
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n'%(err, stdout, stderr), 'DVIPSError')
        raise DVIPSError(stderr+'\n'+stdout)

    runGhostscript(fName, res, 'pnggray')
    bboxes = re.split('\n', runGhostscript(fName, res, 'bbox'))

    for code, i in map(None, codeToRender, range(0, len(codeToRender))):
        dotstartx = -1; dotendx = -1; dotstarty = -1; dotendy = -1; x = 0; widentop = 0; widenbottom = 0
        letterstartx = -1; chopx = 0
        newFileName = fileNameFor(code, charheightpx, imageExtension)
        start_x, start_y, end_x, end_y = map(float, re.match(r'%%HiResBoundingBox: ([0-9\.]+) ([0-9\.]+) ([0-9\.]+) ([0-9\.]+)', bboxes[2*i+1]).groups())
        xsize = ((end_x - start_x) * res)/ptperinch
        ysize = ((end_y - start_y) * res)/ptperinch
        if (xsize <= 0): xsize = 1
        if (ysize <= 0): ysize = 1
        start_x = start_x*res/ptperinch
        start_y = start_y*res/ptperinch
        imname = '%s-%03d.png'%(fName,i+1)
        im = Image.open(os.path.join(workingDir, imname))
        cropdim = (start_x, im.size[1]-start_y-ysize, start_x+xsize, im.size[1]-start_y)
        cropdim = map(int, map(round, cropdim))
        im = im.crop(cropdim)
        if 1 or not re.match(r'^(?:\$|\\\()', code):
            im2 = Image.new('RGB', im.size, (255,255,255))
            im2.paste(im, (0,0))
            alpha = ImageChops.invert(im2.convert('L'))
            im3 = Image.new('RGBA', im.size, (0,0,0))
            im3.putalpha(alpha)
            im3.save(os.path.join(workingDir, newFileName), "PNG")
            continue
        for x in range(0,im.size[0]):  # Try to find the leading dot
            if(dotendy < 0) :
                for y in range(0, im.size[1]):
                    if(dotstarty >= 0 and dotendy < 0): 
                        if(im.getpixel((x,y)) == 255): 
                            dotendy = y
                            break
                    if(dotstarty < 0 and im.getpixel((x,y)) != 255): 
                        dotstartx = x
                        dotstarty = y
                else:
                    dotendy = im.size[1]-1
            elif(dotendx < 0):
                if(charheightpx >= 12):
                    if(im.getpixel((x,round((dotstarty+dotendy)/2.0))) == 255): 
                        dotendx = x
                else:
                    dotendx = 0+dotendy-dotstartx
            else:
                if(charheightpx <= 12): letterstartx = dotendy-dotstarty
                else:
                    for y in range(0,im.size[1]):
                        if(im.getpixel((x,y)) != 255): 
                            letterstartx = x
                            break
                if(letterstartx >= 0): break
        else:
            log('dotstartx=%d, dotendx=%d, dotstarty=%d, dotendy=%d, letterstartx=%d\n'%(dotstartx, dotendx, dotstarty, dotendy, letterstartx))
            log('Unable to find dot. (size=%dx%d)\n'%(im.size[0],im.size[1]), 'renderNonExistingImages')
            errors = 'The following code:\n'+code+'\ngenerated a blank page'
            return escape(errors)
        #log('dotstartx=%d, dotendx=%d, dotstarty=%d, dotendy=%d, letterstartx=%d, alignfudge=%d\n'%(dotstartx, dotendx, dotstarty, dotendy, letterstartx, alignfudge))
        #log('top dot = %d, bottom dot = %d'%(im.getpixel((dotstartx,dotstarty)), im.getpixel((dotstartx,dotendy-1))))
        centerline = (dotendy+dotstarty)/2.0        # 1st guess, centerline is middle of dot
#        centerline += (dotendy-dotstarty)*0.625     # centerline is 5/8 way down the dot.
#                                                    # if dot is not pixel-aligned, take that into account
        centerline += (im.getpixel((dotstartx,dotendy-1)) - im.getpixel((dotstartx,dotstarty)))/(255.0)
        centerline += alignfudge
        bottomsize = im.size[1]-centerline               # pixels below midline
        topsize = centerline                             # pixels above midline
        if(topsize > bottomsize):
            newheight = 2*topsize
            widenbottom = topsize - topsize
        else: 
            newheight = 2*bottomsize
            widentop = bottomsize - topsize
        chopx = round((dotendx-dotstartx)*1.5)           # chop off dot at 1.5 times its width
        if(chopx > letterstartx): chopx = letterstartx   # or where the first letter starts
        im2 = Image.new('RGB', (im.size[0]-chopx, int(round(newheight))), (255,255,255))
        im2.paste(im, (-chopx, int(round(widentop))))
        #log("code='%s' res=%d, topsize=%f, bottomsize=%f, centerline = %f, newheight=%f, widentop=%f, widenbottom=%f, chopx=%f\n"%(code, res, topsize, bottomsize, centerline, newheight, widentop, widenbottom, chopx))
        alpha = ImageChops.invert(im2.convert('L'))
        im3 = Image.new('RGBA', im2.size, (0,0,0))
        im3.putalpha(alpha)
        im3.save(os.path.join(workingDir, newFileName), "PNG")
    os.system('cd %s; rm -f *.log *.aux *.tex *.pdf *.dvi *.ps %s-???.png'%(workingDir, fName))
    return escape(errors)

# Make our file descriptors nonblocking so that reading doesn't hang.
def makeNonBlocking(f):
    fl = fcntl.fcntl(f.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(f.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
def runCommand(cmdLine):
    program = popen2.Popen3('cd %s; '%(workingDir) + cmdLine, 1)
    program.tochild.close()
# old code
#    stderr = ''
#    stdout = ''
#    while(not os.WIFEXITED(program.poll())):
#        stderr = stderr + program.childerr.read()
#        stdout = stdout + program.fromchild.read()
#    status = program.poll()
# new code
    makeNonBlocking(program.fromchild)
    makeNonBlocking(program.childerr)
    stderr = []
    stdout = []
    erreof = False
    outeof = False
    while(not (erreof and outeof)):
        readme, writme, xme = select.select([program.fromchild, program.childerr], [], [])
        for output in readme:
            if(output == program.fromchild):
                text = program.fromchild.read()
                if(text == ''): outeof = True
                else: stdout.append(text)
            elif(output == program.childerr):
                text = program.childerr.read()
                if(text == ''): erreof = True
                else: stderr.append(text)
    status = program.wait()
    error = os.WEXITSTATUS(status) or not os.WIFEXITED(status)
#    return error, stdout, stderr
    return error, string.join(stdout, ''), string.join(stderr, '')

def runLatex(code, charheightpx, latexTemplate):
    texfileName = fileNameFor(code, charheightpx, '.tex')
    dvifileName = fileNameFor(code, charheightpx, '.dvi')
    psfileName = fileNameFor(code, charheightpx, '.ps')
    #cmdLine = 'pdflatex --interaction errorstopmode %s' %(texfileName)
    cmdLine = '/usr/bin/latex %s' %(texfileName)

    file = open(os.path.join(workingDir, texfileName), 'w')
    file.write(latexTemplate %(code,))
    file.close()
    err, stdout, stderr = runCommand(cmdLine)
# Process Graphviz .dot files
    again = 0
    for f in os.listdir(workingDir):
      if re.search(r'\.dot$',f):
        dotfileName = os.path.join(workingDir,f)
        err, stdout, stderr = runCommand(
          'dot -Tps -o %s %s'%(re.sub(r'dot$','ps',dotfileName),
          dotfileName))
        os.remove(dotfileName)
        again = 1
  # repeat LaTeX command if necessary
    if again==1:
      err, stdout, stderr = runCommand(cmdLine)
    if err:
        out = stderr + '\n' + stdout
        err = re.search('!.*\?', out, re.MULTILINE+re.DOTALL)
        if err:
            out = err.group(0)
        raise LatexSyntaxError(out)
    else:
        err, stdout, stderr = runCommand('/usr/local/teTeX/bin/i686-pc-linux-gnu/dvips -o %s %s'%(psfileName, dvifileName))
    
def runGhostscript(fName, res, device):
    input, output = fName+'.ps', fName+'-%03d.png'
    cmdLine = 'gs -dDOINTERPOLATE -dTextAlphaBits=4 ' + \
              '-dGraphicsAlphaBits=4 -r%d -sDEVICE=%s ' + \
              '-dBATCH -dNOPAUSE -dQUIT -sOutputFile=%s %s '
# -dAlignToPixels=1 (doesn't seem to do anything with gs 7.03.
    cmdLine = cmdLine %(res, device, output, input)
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n'%(err, stdout, stderr), 'GhostscriptError')
        raise GhostscriptError(stderr+'\n'+stdout)
    return stderr # when using bbox, BoundingBox is on stderr

