""" 
zwikiexport.py - export a set of zwiki pages as static files.

(c) 2005 SKWM, GNU GPL.

Usage:

   cd directorytoreceivefiles
   zopectl run .../ZWiki/tools/zwikiexport.py [opts] /path/to/wikipageorfolder

Options:

  -h, --help     show this help message and exit
  -n, --dry-run  Don't actually import anything. May be inaccurate.
  -v, --verbose  Be more verbose.

Notes/stories:
export a page
export offspring
export files & images
export a whole wiki
export to var directory
and/or download as a tarball
run from web or commandline or both ?
page type is reflected in file suffix
allow exporting only newer objects
allow round trip with zwikiimport
"""

# placeholder.. in progress

import os, re
from optparse import OptionParser
from zExceptions import *
from OFS.content_types import guess_content_type

try: from transaction import get as get_transaction
except ImportError: pass


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
            
#def doPage(parent,name,text,type):
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

#def doFile(context,filename,data):
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

def exportObj(path,dir):
    """Export a zope folder/wikipage/file/image as one or more files."""
    dlog('exportFile(%s,%s)' % (path,dir))
    vlog(path,newline=False)
    obj = objectFromPath(path)
    if obj.meta_type == 'ZWiki Page':
        # create(/replace/delete) a file representing this page
        filename = os.path.basename(path)
        pagename,ext = os.path.splitext(os.path.basename(filepath))
        if re.match('(?i).htm',ext):
            text = bodyFromHtml(open(filepath).read())
            if text != None:
                vlog(filepath,newline=False)
                doPage(context,pagename, text, 'html')
        else:
            vlog(filepath,newline=False)
            doFile(context, filename, open(filepath).read())
#    else:
#        # create(/replace/delete) a page representing this directory/node
#        # (unless it's the very first directory).
#        # if the directory contains a page with the same name or
#        # index.htm, we will use that for content.
#        vlog(filepath,newline=False)
#        dirpagename = pageNameFromPath(filepath)
#        if dirpagename == '' or doPage(context, dirpagename, '', 'html'):
#            dirpage = context.pageWithName(dirpagename) or context
#            dirpagetext = ''
#            for f in os.listdir(filepath):
#                pagename,ext = os.path.splitext(os.path.basename(f))
#                if (re.match('(?i).htm',ext) and
#                    pagename == dirpagename or
#                    re.match(r'(?i)index$',pagename)):
#                    dirpagetext = open(os.path.join(filepath,f)).read()
#                else:
#                    importFile(dirpage,os.path.join(filepath,f))
#            if dirpagetext:
#                dirpagetext = fixLinksIn(dirpagetext)
#                context.pageWithName(dirpagename).edit(text=dirpagetext)

def pageNameFromPath(path):
    """Derive a suitable wiki page name from a filesystem path."""
    return os.path.splitext(os.path.basename(path))[0]

def objectFromPath(path):
    """Get the object indicated by a ZODB path, or None if not found."""
    return app.restrictedTraverse(path, None)

def main():
    """Main procedure."""
    parseArgs()
    exportObj(args[0], '.')

if __name__ == "__main__":
    main()

#def _test():
#    import doctest, zwikiimport
#    return doctest.testmod(zwikiimport)
#if __name__ == "__main__":
#    _test()
