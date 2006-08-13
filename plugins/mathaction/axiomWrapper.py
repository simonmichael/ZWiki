###
###  Runs Axiom and returns a latex code block for each Axiom block
###

import os, sys, re, popen2, glob
import zLOG
from util import fileNameFor, workingDir
from cgi import escape

# For testing without Zope
#workingDir = './'
#def fileNameFor(code,num,ext):
#    return 'axiom'+ext

class AxiomSyntaxError(Exception): pass

axiomTemplate = r""")set output algebra off
)set output tex on
)set message autoload off
)set quit unprotected
%s)quit
"""

outputPattern = r'(.*?)\s*\n\(\d+\) -> '
reConsts = re.MULTILINE+re.DOTALL

def log(message,summary='',severity=0):
        zLOG.LOG('LatexWikiDebugLog',severity,summary,message)

def renderAxiom(axiomCodeList):
    def securityCheck(code):
      newCode = re.compile(r'^[ \t]*\)sys([^\n]*)',reConsts).sub(r'-- not allowed: )sys\1\n)sys',code)
#     newCode = re.compile(r'^[ \t]*\)lisp([^\n]*)',reConsts).sub(r'-- not allowed: )lisp\1\n)sys',newCode)
      newCode = re.compile(r'^[ \t]*\)fin([^\n]*)',reConsts).sub(r'-- not allowed: )fin\1\n)sys',newCode)
      newCode = re.compile(r'^[ \t]*\)spool([^\n]*)',reConsts).sub(r'-- not allowed: )spool\1\n)sys',newCode)
      return newCode
    
    n = 0
    unifiedCode = ''
    for axiomCode in axiomCodeList:
        newAxiomCode = securityCheck(axiomCode)
        n = n + 1
        if re.match(r'^\s*\)abb',newAxiomCode):
            # Starts like spad so compile as library code
            axiomFileName = os.path.join(workingDir,fileNameFor(newAxiomCode, 25, '.%3.3d.spad'%n))
            unifiedCode = unifiedCode + ')set message prompt none\n'
            unifiedCode = unifiedCode + ')sys cat %s\n'%axiomFileName
            unifiedCode = unifiedCode + ')compile %s\n'%axiomFileName
            unifiedCode = unifiedCode + ')set message prompt step\n'
        elif re.match(r'^\\begin *{spad}\s*.*?\s*\\end *{spad}',newAxiomCode,
             reConsts):
            # spad so compile as library code
            m = re.match(r'^\\begin *{spad}\s*(.*?)\s*\\end *{spad}',
                newAxiomCode,reConsts)
            newAxiomCode = m.group(1) # just the spad code
            axiomFileName = os.path.join(workingDir,fileNameFor(newAxiomCode, 25, '%3.3d.spad'%n))
            unifiedCode = unifiedCode + ')set message prompt none\n'
            unifiedCode = unifiedCode + ')sys echo "<spad>";cat %s;echo "</spad>"\n'%axiomFileName
            unifiedCode = unifiedCode + ')compile %s\n'%axiomFileName
            unifiedCode = unifiedCode + ')set message prompt step\n'
        elif re.match(r'^\\begin *{aldor}\s*.*?\s*\\end *{aldor}',newAxiomCode,
             reConsts):
            # aldor so compile as library code
            m = re.match(r'^\\begin *{aldor} *(?:\[(.*?)\])?\s*(.*?)\s*\\end *{aldor}',
                newAxiomCode,reConsts)
            if m.group(1): # optional file name
                axiomFileName = os.path.join(workingDir,m.group(1)+'.as')
            else :
                axiomFileName = os.path.join(workingDir,fileNameFor(newAxiomCode, 25, '%3.3d.as'%n))
            newAxiomCode = m.group(2) # just the aldor code
            unifiedCode = unifiedCode + ')set message prompt none\n'
            unifiedCode = unifiedCode + ')sys echo "<aldor>";cat %s;echo "</aldor>"\n'%axiomFileName
            unifiedCode = unifiedCode + ')compile %s\n'%axiomFileName
            unifiedCode = unifiedCode + ')set message prompt step\n'
        elif re.match(r'^\\begin *{boot}\s*.*?\s*\\end *{boot}',newAxiomCode, reConsts):
            m = re.match(r'^\\begin *{boot}\s*(.*?)\s*\\end *{boot}',
                newAxiomCode,reConsts)
            newAxiomCode = m.group(1) # just the boot code
            fileName = fileNameFor(newAxiomCode, 25, '%3.3d'%n)
            axiomFileName = os.path.join(workingDir,fileName+'.boot')
            axiomFileName2 = fileName+'.clisp'
            unifiedCode = unifiedCode + ')set message prompt none\n'
            unifiedCode = unifiedCode + ')sys echo "<boot>";cat %s;echo "</boot>"\n'%axiomFileName
            unifiedCode = unifiedCode + ')lisp (boottran::boottocl "%s")\n'%axiomFileName
            unifiedCode = unifiedCode + ')lisp (load (compile-file (truename (concat (si:getenv "AXIOM") "/../../int/interp/%s"))))\n'%axiomFileName2
            unifiedCode = unifiedCode + ')set message prompt step\n'
        elif re.match(r'^\\begin *{lisp}\s*.*?\s*\\end *{lisp}',newAxiomCode, reConsts):
            m = re.match(r'^\\begin *{lisp}\s*(.*?)\s*\\end *{lisp}',
                newAxiomCode,reConsts)
            newAxiomCode = m.group(1) # just the lisp code
            axiomFileName = os.path.join(workingDir,fileNameFor(newAxiomCode, 25, '%3.3d.lisp'%n))
            unifiedCode = unifiedCode + ')set message prompt none\n'
            unifiedCode = unifiedCode + ')sys echo "<lisp>";cat %s;echo "</lisp>"\n'%axiomFileName
            unifiedCode = unifiedCode + ')lisp (load (compile-file "%s"))\n'%axiomFileName
            unifiedCode = unifiedCode + ')set message prompt step\n'
        else:
            # otherwise it is just an input file
            axiomFileName = os.path.join(workingDir,fileNameFor(newAxiomCode, 25, '.%3.3d.input'%n))
            unifiedCode = unifiedCode + ')read %s\n'%axiomFileName
        axiomFile = open(axiomFileName, 'w')
        axiomFile.write(newAxiomCode)
        axiomFile.close()
    if unifiedCode:
        try:
            latexCode=runAxiom(unifiedCode,axiomTemplate)
            latexCodeList = re.compile(outputPattern, reConsts).findall(latexCode)
            return (latexCodeList,'')
        except AxiomSyntaxError, data:
            errors = str(data)
            log(errors, 'AxiomSyntaxError')
            return ([],escape(errors))
    return ([],'')

def runCommand(cmdLine):
    program = popen2.Popen3('cd %s; '%(workingDir) + cmdLine, 1, 4096)
    program.tochild.close()
    stderr = ''
    stdout = ''
    while(not os.WIFEXITED(program.poll())):
#       Seems Axiom doesn't properly close stderr
#       stderr = stderr + program.childerr.read()
        stdout = stdout + program.fromchild.read()
    program.fromchild.close()
    program.childerr.close()
    status = program.poll()
    error = os.WEXITSTATUS(status) or not os.WIFEXITED(status)
    return error, stdout, stderr

def runAxiom(axiomCode, axiomTemplate):
    axiomFileName = os.path.join(workingDir,fileNameFor(axiomCode, 25, '.axm'))
    # problem: http://wiki.axiom-developer.org/145PipingCommandsToSmanDoesNotWork
    #cmdLine = '/usr/bin/axiom < %s' %(axiomFileName)
    #cmdLine = 'export AXIOM=/usr/local/axiom/mnt/linux; export PATH=$AXIOM/bin:$PATH; export ALDORROOT=/usr/local/aldor/linux/1.0.2; export PATH=$ALDORROOT/bin:$PATH; export HOME=/var/lib/plone2/main; AXIOMsys < %s' %(axiomFileName)
    # enough for now on debian
    cmdLine = 'export AXIOM=/usr/lib/axiom-20050901; $AXIOM/bin/AXIOMsys < %s' %(axiomFileName)
    file = open(axiomFileName, 'w')
    file.write(axiomTemplate%axiomCode)
    file.close()
    err, stdout, stderr = runCommand(cmdLine)
 
    if err:
        out = 'Error: ' + cmdLine + '\n' + stderr + '\n' + stdout
        raise AxiomSyntaxError(out)
    else:
        # Clean up the startup prompts
        newcode = re.compile(r'^.*?(?:\(1\) -> ){5}', reConsts).sub('',stdout)
        # Temporary fix for Axiom bug \spadcommand{radix(10**90,32)}
        newcode = re.compile(r'#\\', reConsts).sub('',newcode)
        return newcode
    
