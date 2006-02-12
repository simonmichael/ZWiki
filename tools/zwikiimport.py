""" 
zwikiimport.py - import files/directories into a zwiki.

(c) 2004-2005 SKWM, GNU GPL.

Usage:

   cd directorycontainingfiles
   zopectl run .../ZWiki/tools/zwikiimport.py [opts] /path/to/wikipageorfolder

Options:

  -h, --help     show this help message and exit
  -n, --dry-run  Don't actually import anything. May be inaccurate.
  -v, --verbose  Be more verbose.
  --debug        Print additional debug information.
  --replace      When objects already exist, replace them.
  --delete       Delete existing objects instead of importing.

Notes/stories/todos:
-zope root folder or root page is specified as an argument
-we walk the current directory
-each text file becomes a wiki page by the same name
-a subdirectory becomes a page. the contents are imported and parented under it
-a file named after its directory or index.html? is merged with the directory page
-images become images, files become files
-relative links and image paths are adjusted
-allow ignoring/replacing/deleting old pages (as long wiki is anon-writable)
todo:
suffixes influence the page type: .html, .stx, .rst, .txt etc.
an id collision creates a page with modified name
a front page may be selected from the imported pages
text patterns may be removed from the pages
file(s) may be specified on the command line
use cmf or plone image/files when appropriate
images and files have safe ids assigned if needed
use visitor pattern
smarter dry run
get around anon-writable requirement of zwiki web api
apply html tidy automatically ?

"""

import os, re
from optparse import OptionParser
from zExceptions import *
import OFS.Image
from OFS.content_types import guess_content_type

try: from transaction import get as get_transaction
except ImportError: pass

from os import environ
from sys import stdin, stdout
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

options = args = None

def parseArgs():
    """Parse command-line options."""
    global options, args
    parser = OptionParser()
    parser.add_option('-n', '--dry-run', action='store_true',dest='dryrun',
                      help="Don't actually import anything (may be inaccurate)")
    parser.add_option('-v', '--verbose', action='store_true',
                      help="Be more verbose")
    parser.add_option('--debug', action='store_true',
                      help="Print additional debug information")
    #parser.add_option('--ignore', action='store_true',
    #                  help="When objects already exist, ignore and continue")
    parser.add_option('--replace', action='store_true',
                      help="When objects already exist, replace them")
    parser.add_option('--delete', action='store_true',
                      help="Delete existing objects instead of importing")
    #parser.add_option('-u','--user',
    #                  help="user:password for authentication")
    options,args = parser.parse_args()
    # to facilitate calling authentication-requiring API methods,
    # set up a dummy request with the provided credentials
    #if options.user:
    #    user, password = options.user.split(':')
    #    options.request = makerequest(app,user,password)
    #else:
    #    options.request = None
    # XXX doesn't work yet
    options.request = None

# XXX doesn't work yet
def makerequest(app,user,password):
    """Like Testing.makerequest but add authentication info."""
    resp = HTTPResponse(stdout=stdout)
    environ['SERVER_NAME']='foo'
    environ['SERVER_PORT']='80'
    environ['REQUEST_METHOD'] = 'GET'
    environ['AUTHENTICATED_USER'] = user
    environ['__ac_name'] = user
    environ['__ac_password'] = password
    req = HTTPRequest(stdin, environ, resp)
    return app.__of__(RequestContainer(REQUEST = req))

def dlog(msg='', newline=True):
    """Print some text and/or a newline if debug option is true."""
    if options.debug:
        if newline:
            print '* %s' % msg
        else:
            print '* %s' % msg,

def vlog(msg='', newline=True):
    """Print some text and/or a newline if verbose option is true."""
    if options.verbose: 
        if newline:
            print '%s' % msg
        else:
            print '%s' % msg,
            
def bodyFromHtml(t):
    """Return contents of html body tag in t, or None."""
    m = re.search(r'(?is)<body[^>]*>(.*)</body>',t)
    if m: return m.group(1)
    else: return None

def fixLinksIn(t):
    """Fix up relative hyperlinks and image paths for the wiki.

    NB doesn't work after html tidy."""
    # strip path components from relative links
    t = re.sub(r'(?i)( (href|src)=")(?!http:)([^"/]+/)+?(?P<last>[^"/]+)"',
               r'\1\g<last>"',
               t)
    # strip .htm suffix
    t = re.sub(r'(?i)( (href|src)=")(?!http:)(?P<name>[^"]+).html?"',
               r'\1\g<name>"',
               t)
    # fuzzy urls should take care of whitespace/quoting/capitalization diffs
    return t

def doPage(parent,name,text,type):
    """Create, modify or delete the specified wiki page under the parent page.

    Prints a status message and returns a boolean for success/failure.
    """
    dlog('doFile(%s,...,%s)' % (name,type))
    if options.dryrun:
        vlog(': dry run')
        return True
    existing = parent.pageWithName(name)
    #if existing and options.ignore:
    #    vlog(': ignored')
    #    return True
    if existing and options.delete:
        existing.delete(REQUEST=options.request)
        get_transaction().commit()
        vlog(': deleted')
        return True
    elif existing and options.replace:
        text = fixLinksIn(text)
        existing.edit(name, text, type, REQUEST=options.request)
        get_transaction().commit()
        vlog(': replaced')
        return True
    else:
        try:
            text = fixLinksIn(text)
            parent.create(name, text, type, REQUEST=options.request)
            get_transaction().commit()
            vlog(': created')
            return True
        except BadRequest, e:
            vlog(': failed\n*** (%s)' % e)
            return False

def doFile(context,filename,data):
    """Create, modify or delete the specified file or image.

    An Image is created if the file suffix indicates it.
    Prints a status message and returns a boolean for success/failure.
    """
    dlog('doFile(%s,...)' % (filename))
    if options.dryrun:
        vlog(': dry run')
        return True
    folder = context.folder()
    existing = getattr(folder,filename,None)
    #if existing and options.ignore:
    #    vlog(': ignored')
    #    return True
    if existing and options.delete:
        folder._delObject(filename)
        get_transaction().commit()
        vlog(': deleted')
        return True
    elif existing and options.replace:
        folder._getOb(filename).manage_upload(data)
        get_transaction().commit()
        vlog(': replaced')
        return True
    else:
        try:
            if guess_content_type(filename)[0][0:5] == 'image':
                folder._setObject(filename, OFS.Image.Image(filename,filename,''))
            else:
                folder._setObject(filename, OFS.Image.File(filename,filename,''))
            folder._getOb(filename).manage_upload(data)
            get_transaction().commit()
            vlog(': created')
            return True
        except BadRequest, e:
            vlog(': failed\n*** (%s)' % e)
            return False

def importFile(context,filepath):
    """Import a file or directory tree as wiki page/file/image objects."""
    dlog('importFile(%s,%s)' % (`context`,filepath))
    vlog(filepath,newline=False)
    if os.path.isfile(filepath):
        # create(/replace/delete) a wiki page based on file name & content
        filename = os.path.basename(filepath)
        pagename,ext = os.path.splitext(os.path.basename(filepath))
        if re.match('(?i).htm',ext):
            text = bodyFromHtml(open(filepath).read())
            if text != None:
                vlog(filepath,newline=False)
                doPage(context,pagename, text, 'html')
        else:
            vlog(filepath,newline=False)
            doFile(context, filename, open(filepath).read())
    else:
        # create(/replace/delete) a page representing this directory/node
        # (unless it's the very first directory).
        # if the directory contains a page with the same name or
        # index.htm, we will use that for content.
        vlog(filepath,newline=False)
        dirpagename = pageNameFromPath(filepath)
        if dirpagename == '' or doPage(context, dirpagename, '', 'html'):
            dirpage = context.pageWithName(dirpagename) or context
            dirpagetext = ''
            for f in os.listdir(filepath):
                pagename,ext = os.path.splitext(os.path.basename(f))
                if (re.match('(?i).htm',ext) and
                    pagename == dirpagename or
                    re.match(r'(?i)index$',pagename)):
                    dirpagetext = open(os.path.join(filepath,f)).read()
                else:
                    importFile(dirpage,os.path.join(filepath,f))
            if dirpagetext:
                dirpagetext = fixLinksIn(dirpagetext)
                context.pageWithName(dirpagename).edit(text=dirpagetext)

def pageNameFromPath(path):
    """Derive a suitable wiki page name from a filesystem path."""
    return os.path.splitext(os.path.basename(path))[0]

def pageFromPath(path):
    """Get the wiki page object indicated by a ZODB path.

    If it's a folder, return the first page. Otherwise None."""
    obj = app.restrictedTraverse(path, None)
    if not obj:
        return None
    if 'Folder' in obj.meta_type:
        pages = obj.objectValues(spec='ZWiki Page')
        if pages:
            obj = pages[0]
    if obj.meta_type == 'ZWiki Page':
        return obj
    else:
        return None

def main():
    """Main procedure."""
    parseArgs()
    importFile(pageFromPath(args[0]), '.')
    get_transaction().commit()

if __name__ == "__main__":
    main()

#def _test():
#    import doctest, zwikiimport
#    return doctest.testmod(zwikiimport)
#if __name__ == "__main__":
#    _test()
