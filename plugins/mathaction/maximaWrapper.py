###
###  Runs Maxima and returns a latex code block for each Maxima block
###

import os, sys, re, popen2, glob
import zLOG
from util import fileNameFor, workingDir
from cgi import escape

# For testing without Zope
#workingDir = './'
#def fileNameFor(code,num,ext):
#    return 'maxima'+ext

class MaximaSyntaxError(Exception): pass

maximaTemplate = """%s
quit();
"""

# Throw away the prompts - we only need the <latex> .. </latex>
outputSplit = '<prompt>.*</prompt>\nbatching #p.*\n'
reConsts = re.MULTILINE+re.DOTALL

def log(message,summary='',severity=0):
        zLOG.LOG('LatexWikiDebugLog',severity,summary,message)

def renderMaxima(maximaCodeList):
    def securityCheck(code):
      return code
    
    n = 0
    unifiedCode = ''
    for maximaCode in maximaCodeList:
        newMaximaCode = securityCheck(maximaCode)
        n = n + 1
        maximaFileName = os.path.join(workingDir,fileNameFor(newMaximaCode, 25, '.%3.3d.max'%n))
        unifiedCode = unifiedCode + 'batch("%s");\n'%maximaFileName
        maximaFile = open(maximaFileName, 'w')
        maximaFile.write(newMaximaCode)
        maximaFile.close()
    if unifiedCode:
        try:
            latexCode=runMaxima(unifiedCode,maximaTemplate)
            latexCodeList = re.split(outputSplit,latexCode)[1:]
            return (latexCodeList,'')
        except MaximaSyntaxError, data:
            errors = str(data)
            log(errors, 'MaximaSyntaxError')
            return ([],escape(errors))
    return ([],'')

def runCommand(cmdLine):
    program = popen2.Popen3('cd %s; '%(workingDir) + cmdLine, 1, 4096)
    program.tochild.close()
    stderr = ''
    stdout = ''
    while(not os.WIFEXITED(program.poll())):
        stdout = stdout + program.fromchild.read()
    program.fromchild.close()
    program.childerr.close()
    status = program.poll()
    error = os.WEXITSTATUS(status) or not os.WIFEXITED(status)
    return error, stdout, stderr

def runMaxima(maximaCode, maximaTemplate):
    maximaFileName = os.path.join(workingDir,fileNameFor(maximaCode, 25, '.mbat'))
    cmdLine = '/usr/bin/maxima -p /zope1/Products/ZWiki/plugins/mathaction/mathaction-maxima-5.9.3.lisp < %s' %(maximaFileName)
    file = open(maximaFileName, 'w')
    file.write(maximaTemplate%maximaCode)
    file.close()
    err, stdout, stderr = runCommand(cmdLine)
 
    if err:
        out = 'Error: ' + cmdLine + '\n' + stderr + '\n' + stdout
        raise MaximaSyntaxError(out)
    else:             # don't want the final prompt
        return re.sub(r'<prompt>.*</prompt></maxima>$',r'',stdout)
