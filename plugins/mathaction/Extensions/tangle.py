import os, sys, popen2, select, fcntl, string, zLOG
from cStringIO import StringIO
class NowebError(Exception): pass

def tangle(self, REQUEST, RESPONSE):

  """notangle output
  """

  def n2rn(s):
    return s.replace('\n', '\r\n')

  # Make our file descriptors nonblocking so that reading doesn't hang.
  def makeNonBlocking(f):
    fl = fcntl.fcntl(f.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(f.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)

  def runCommand(cmdLine,stdin):
    program = popen2.Popen3(cmdLine, 1)
    program.tochild.write(stdin)
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

  def log(message,summary='',severity=0):
        zLOG.LOG('LatexWikiDebugLog',severity,summary,message)

  def runTangle(stdin,chunk):
    cmdLine = "/usr/bin/notangle -R'%s' -"%chunk
    err, stdout, stderr = runCommand(cmdLine,stdin)
    if err:
        log('%s\n%s\n%s\n%s\n'%(cmdLine, err, stdout, stderr), 'NowebError')
        raise NowebError(stderr+'\n'+stdout)
    return stdout

  RESPONSE.setHeader('Content-Type', 'text/plain')
  # RESPONSE.setHeader('Content-Disposition', 'attachment; filename="%s"' % self.getId())
  return n2rn(runTangle(self.document(),REQUEST.chunk))


