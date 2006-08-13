###
###  Runs REDUCE and returns a latex code block for each REDUCE block
###

import os, sys, re, popen2, glob
import zLOG
from util import fileNameFor, workingDir
from cgi import escape

# For testing without Zope
#workingDir = './'
#def fileNameFor(code,num,ext):
#    return 'reduce'+ext

class ReduceSyntaxError(Exception): pass

#reduceTemplate = r"""off INT;
#load_package rlfi;
#on latex;
#%s
#bye;
#"""
reduceTemplate = r"""off INT;
load_package tri;
on texbreak;
%s
bye;
"""

outputPattern = r'1: (.*?)(?:\004\n\*{5} End-of-file[^\n]\s*|\s*\n(?=1: )|\s+$)'
reConsts = re.DOTALL
#reConsts = re.MULTILINE+re.DOTALL

def log(message,summary='',severity=0):
        zLOG.LOG('LatexWikiDebugLog',severity,summary,message)

def renderReduce(reduceCodeList):
    def securityCheck(code):
#     newCode = re.compile(r'^[ \t]*\)sys([^\n]*)',reConsts).sub(r'-- not allowed: )sys\1\n)sys',code)
      newCode = code
      return newCode
    
    n = 0
    unifiedCode = ''
    for reduceCode in reduceCodeList:
        newReduceCode = securityCheck(reduceCode)
        n = n + 1
        if re.match(r'^\s*\)abbrev',newReduceCode):
            # Starts like a package so compile as library code
            reduceFileName = os.path.join(workingDir,fileNameFor(newReduceCode, 25, '.%3.3d.red'%n))
            unifiedCode = unifiedCode + 'compile "%s";\n'%reduceFileName
        else:
            # otherwise it is just an input file
            reduceFileName = os.path.join(workingDir,fileNameFor(newReduceCode, 25, '.%3.3d.rin'%n))
            unifiedCode = unifiedCode + 'in "%s";\n'%reduceFileName
        reduceFile = open(reduceFileName, 'w')
        reduceFile.write(newReduceCode)
        reduceFile.close()
    if unifiedCode:
        try:
            latexCode=runReduce(unifiedCode,reduceTemplate)
            latexCodeList = re.compile(outputPattern, reConsts).findall(latexCode)
            return (latexCodeList,'')
        except ReduceSyntaxError, data:
            errors = str(data)
            log(errors, 'ReduceSyntaxError')
            return ([],escape(errors))
    return ([],'')

def runCommand(cmdLine):
    program = popen2.Popen3('cd %s; '%(workingDir) + cmdLine, 1, 4096)
    program.tochild.close()
    stderr = ''
    stdout = ''
    while(not os.WIFEXITED(program.poll())):
#       Just in case REDUCE doesn't properly close stderr
#       stderr = stderr + program.childerr.read()
        stdout = stdout + program.fromchild.read()
    program.fromchild.close()
    program.childerr.close()
    status = program.poll()
    error = os.WEXITSTATUS(status) or not os.WIFEXITED(status)
    return error, stdout, stderr

def runReduce(reduceCode, reduceTemplate):
    reduceFileName = os.path.join(workingDir,fileNameFor(reduceCode, 25, '.run'))
    cmdLine = 'export PATH=/usr/local/bin:$PATH;reduce < %s' %(reduceFileName)
    file = open(reduceFileName, 'w')
    file.write(reduceTemplate%reduceCode)
    file.close()
    err, stdout, stderr = runCommand(cmdLine)
 
    if err:
        out = 'Error: ' + cmdLine + '\n' + stderr + '\n' + stdout
        raise ReduceSyntaxError(out)
    else:
        # Clean up the startup prompts
        newcode = re.compile(r'^(?:.*?1: ){3}', reConsts).sub('',stdout)
        return newcode
