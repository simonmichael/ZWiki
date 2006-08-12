
import os, sys, re, zLOG, popen2, select, fcntl, string
from struct import pack, unpack

## path to use as src prefix in img tag
imagesPath = 'images/'
# Actual location of images
workingDir = sys.modules['__builtin__'].CLIENT_HOME + '/LatexWiki'
# Default character size, if the user doesn't specify 
defaultcharsizepx = 18

imageExtension = '.png'

def fileNameFor(latexCode, size, extension=''):
    return '%s-%spx%s' %(abs(hash(latexCode)), size, extension)

def getPngSize(fname,
               magicBytes=pack('!BBBBBBBB', 137, 80, 78, 71, 13, 10, 26, 10)):
    f = file(fname, 'r')
    buf = f.read(24)
    f.close()
    assert buf[:8] == magicBytes, 'in getPngSize, file not a PNG!'
    return tuple(map(int, unpack('!LL', buf[16:24])))

def log(message,summary='',severity=0):
        zLOG.LOG('LatexWikiDebugLog',severity,summary,message)

# Make our file descriptors nonblocking so that reading doesn't hang.
def makeNonBlocking(f):
    fl = fcntl.fcntl(f.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(f.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
def runCommand(cmdLine, input=None):
    program = popen2.Popen3('cd %s; '%(workingDir) + cmdLine, 1)
    if input:
        program.tochild.write(input)
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

def findinpath(exe):
    paths = [exe]
    paths.extend( \
      map(lambda x: os.path.join(x,exe), re.split(':', os.getenv('PATH'))))
    for path in paths:
        if os.access(path, os.X_OK): break
        path = None
    return path

def unique(s):
     """Return a list of the elements in s, but without duplicates.

     For example, unique([1,2,3,1,2,3]) is some permutation of [1,2,3],
     unique("abcabc") some permutation of ["a", "b", "c"], and
     unique(([1, 2], [2, 3], [1, 2])) some permutation of
     [[2, 3], [1, 2]].

     For best speed, all sequence elements should be hashable.  Then
     unique() will usually work in linear time.

     If not possible, the sequence elements should enjoy a total
     ordering, and if list(s).sort() doesn't raise TypeError it's
     assumed that they do enjoy a total ordering.  Then unique() will
     usually work in O(N*log2(N)) time.

     If that's not possible either, the sequence elements must support
     equality-testing.  Then unique() will usually work in quadratic
     time.
     """

     n = len(s)
     if n == 0:
         return []

     # Try using a dict first, as that's the fastest and will usually
     # work.  If it doesn't work, it will usually fail quickly, so it
     # usually doesn't cost much to *try* it.  It requires that all the
     # sequence elements be hashable, and support equality comparison.
     u = {}
     try:
         for x in s:
             u[x] = 1
     except TypeError:
         del u  # move on to the next method
     else:
         return u.keys()

     # We can't hash all the elements.  Second fastest is to sort,
     # which brings the equal elements together; then duplicates are
     # easy to weed out in a single pass.
     # NOTE:  Python's list.sort() was designed to be efficient in the
     # presence of many duplicate elements.  This isn't true of all
     # sort functions in all languages or libraries, so this approach
     # is more effective in Python than it may be elsewhere.
     try:
         t = list(s)
         t.sort()
     except TypeError:
         del t  # move on to the next method
     else:
         assert n > 0
         last = t[0]
         lasti = i = 1
         while i < n:
             if t[i] != last:
                 t[lasti] = last = t[i]
                 lasti += 1
             i += 1
         return t[:lasti]

     # Brute force is all that's left.
     u = []
     for x in s:
         if x not in u:
             u.append(x)
     return u
