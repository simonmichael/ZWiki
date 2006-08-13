"""
Render a pamphlet file as .pamphlet, .dvi and .pdf files

$Id: pamphletWrapper.py,v 0.1 2005/10/07 Bill Page $

TODO:
	1) Preprocess \begin{axiom} ... \end{axiom} pseudo enviroments
	   also {spad} {aldor} and {reduce} as in 'axiomWrapper.py'
	2) Problem with dvipdf so changed to dvipdfm. Hyperref ok?
"""
import os, sys, re, popen2, glob, zLOG, select, fcntl, string
from cgi import escape

class LatexSyntaxError(Exception): pass
class NowebError(Exception): pass
class DviPdfError(Exception): pass
class DviPngError(Exception): pass

def log(message,summary='',severity=0):
        zLOG.LOG('LatexWikiDebugLog',severity,summary,message)

def renderPDF(fDir,fName,pdfMethod):
    """ render body source as PDF.
    """
    os.system("cd '%s'; rm -f '%s.pdf' '%s.ps' '%s.dvi' '%s.tex'"%(fDir,fName,fName,fName,fName))
    errors = ""
    try:
       runNoweb(fDir,fName)
    except NowebError, data:
       errors = str(data)
       log(errors, 'NowebError')
       return escape(errors)

    try:
       runLatex(fDir,fName)
    except LatexSyntaxError, data:
       errors = str(data)
       log(errors, 'LatexSyntaxError')
       return escape(errors)

# twice for good luck (toc and labels)
    try:
       runLatex(fDir,fName)
    except LatexSyntaxError, data:
       errors = str(data)
       log(errors, 'LatexSyntaxError')
       return escape(errors)

    try:
       runDviPs(fDir,fName)
    except DviPdfError, data:
       errors = str(data)
       log(errors, 'DviPdfError')
       return escape(errors)
    if (pdfMethod == 'dvipdfm'):
       try:
          runDviPdfm(fDir,fName)
       except DviPdfError, data:
          errors = str(data)
          log(errors, 'DviPdfError')
          return escape(errors)
    else:
       try:
          runPs2Pdf(fDir,fName)
       except DviPdfError, data:
          errors = str(data)
          log(errors, 'DviPdfError')
          return escape(errors)

    try:
       runDviPng(fDir,fName)
    except DviPngError, data:
       errors = str(data)
       log(errors, 'DviPngError')
       return escape(errors)

    os.system("cd '%s'; rm -f '%s.aux' '%s.toc' '%s.out'"%(fDir,fName,fName,fName))
    return escape(errors)

# Make our file descriptors nonblocking so that reading doesn't hang.
def makeNonBlocking(f):
    fl = fcntl.fcntl(f.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(f.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
def runCommand(cmdLine):
    program = popen2.Popen3(cmdLine, 1)
    program.tochild.close()
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
    return error, string.join(stdout, ''), string.join(stderr, '')

def runNoweb(fDir,fName):
    cmdLine = "cd '%s'; /usr/bin/noweave -delay '%s.pamphlet' > '%s.tex'"%(fDir,fName,fName)
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n%s\n'%(cmdLine, err, stdout, stderr), 'NowebError')
        raise NowebError("noweb: %s\n"%cmdLine+stderr+'\n'+stdout)
    return stderr

def runLatex(fDir,fName):
    cmdLine = "cd '%s'; rm -f *.dot; /usr/bin/latex --interaction nonstopmode '%s.tex'" %(fDir,fName)

    err, stdout, stderr = runCommand(cmdLine)
# Process Graphviz .dot files
    again = 0
    for f in os.listdir(fDir):
      if re.search(r'\.dot$',f):
        dotfileName = os.path.join(fDir,f)
        err, stdout, stderr = runCommand(
          "dot -Tps -o '%s' '%s'"%(re.sub(r'dot$','ps',dotfileName),
          dotfileName))
        if err:
            out = stderr + '\n' + stdout
            raise LatexSyntaxError("dot: %s\n"%cmdLine+out)
        again = 1
  # repeat LaTeX command if necessary
    if again == 1:
      err, stdout, stderr = runCommand(cmdLine)
    if err:
        out = stderr + '\n' + stdout
        err = re.search('!.*\?', out, re.MULTILINE+re.DOTALL)
        if err:
            out = err.group(0)
            raise LatexSyntaxError("latex: %s\n"%cmdLine+out)
    return stderr

def runDviPdfm(fDir,fName):
    cmdLine = "cd '%s'; dvipdfm '%s.dvi'"%(fDir,fName)
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n%s\n'%(cmdLine, err, stdout, stderr), 'DviPdfError')
        raise DviPdfError("dvipdfm: %s\n"%cmdLine+stderr+'\n'+stdout)
    return stderr
 
def runDviPs(fDir,fName):
    cmdLine = "cd '%s'; /usr/bin/dvips -z -o '%s.ps' '%s.dvi'"%(fDir,fName,fName)
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n%s\n'%(cmdLine, err, stdout, stderr), 'DviPdfError')
        raise DviPdfError("dvips: %s\n"%cmdLine+stderr+'\n'+stdout)
    return stderr

def runPs2Pdf(fDir,fName):
    cmdLine = "cd '%s'; ps2pdf14 '%s.ps'"%(fDir,fName)
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n%s\n'%(cmdLine, err, stdout, stderr), 'DviPdfError')
        raise DviPdfError("ps2pdf: %s\n"%cmdLine+stderr+'\n'+stdout)
    return stderr

def runDviPng(fDir,fName):
    cmdLine = "cd '%s'; dvipng -T tight -bg transparent -l 1 '%s.dvi'"%(fDir,fName)
    err, stdout, stderr = runCommand(cmdLine)
    if err:
        log('%s\n%s\n%s\n%s\n'%(cmdLine, err, stdout, stderr), 'DviPngError')
        raise DviPngError("dvipng: %s\n"%cmdLine+stderr+'\n'+stdout)
    return stderr
