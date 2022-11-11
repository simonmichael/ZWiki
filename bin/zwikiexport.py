#!/usr/bin/env python
"""
zwikiexport.py - export a zwiki folder or single page to the filesystem.

(c) 2005-2010 SKWM, GNU GPL.
"""

usage = """\
$INSTANCE/bin/zopectl run %prog /path/to/wiki/folder

Exports the specified wiki folder (or zwiki page) to the current directory.
You'll need to stop the Zope instance first, unless it is a ZEO instance."""

# stories:
# -parse args, show help
# -export a page
# -page type is reflected in file suffix
# -export a whole wiki
# export offspring
# export files & images
# allow exporting only changed objects
# allow round trip with zwikiimport
# run from web ?
# export to var directory
# download as a tarball

import sys, os, re
from optparse import OptionParser

parser = OptionParser(usage=usage)
parser.add_option('-n', '--dry-run', action='store_true',dest='dryrun', help="Don't actually do anything")
parser.add_option('-v', '--verbose', action='store_true', help="Be more verbose")
parser.add_option('-q', '--quiet', action='store_true', help="Be less verbose")

try: app
except NameError: parser.error("this should be run with zopectl run.")

def parseArgs():
    opts, args = parser.parse_args()
    if len(args) != 1: parser.error('one zope object path is required.')
    return opts, args

def main():
    global opts, args
    opts, args = parseArgs()
    exportObjectAt(args[0], '.')

def exportObjectAt(path, fsdir):
    """Export a zope folder/wikipage/file/image as one or more files."""
    vlog('%s: ' % path, newline=False)
    o = objectFromPath(path)
    vlog(getattr(o, 'meta_type', 'none'))
    if hasattr(o, 'meta_type'):
        if o.meta_type == 'ZWiki Page':
            basename, ext, content = o.pageId(), o.pageTypeId(), o.text()
            filepath = os.path.join(fsdir, '%s.%s'%(basename,ext))
            log('%s saved as %s' % (path, filepath))
            if not opts.dryrun:
                f = open(filepath,'w')
                f.write(content)
                f.close()
        elif o.isPrincipiaFolderish and not 'Catalog' in o.meta_type:
            fsdir2 = os.path.join(fsdir, o.getId())
            if not opts.dryrun:
                if not os.path.exists(fsdir2): os.mkdir(fsdir2)
            for o2 in o.objectValues(): exportObjectAt(o2.absolute_url_path(), fsdir2)

def objectFromPath(path):
    """Get the object indicated by a ZODB path, or None if not found."""
    return app.restrictedTraverse(path, None)

def log(msg='', newline=True):
    """Print some text and/or a newline unless quiet option is true."""
    if not opts.quiet:
        if newline:
            print '%s' % msg
        else:
            print '%s' % msg,

def vlog(msg='', newline=True):
    """Print some text and/or a newline if verbose option is true."""
    if opts.verbose:
        if newline:
            print '%s' % msg
        else:
            print '%s' % msg,

if __name__ == "__main__": main()

#def _test():
#    import doctest, zwikiimport
#    return doctest.testmod(zwikiimport)
#if __name__ == "__main__":
#    _test()
