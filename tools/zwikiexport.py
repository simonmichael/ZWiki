""" 
zwikiexport.py - export a set of zwiki pages as static files.

(c) 2004 SKWM, GNU GPL.

Usage:

   cd directorytoreceivefiles
   zopectl run .../Products/ZWiki/tools/zwikiexport.py [options] /path/to/wikifolderorpage

Options:

   -h, --help

   -n, --dry-run

Notes/stories:
export to var directory and/or as a downloadable tarball
run from web or commandline or both ?
export whole wiki
export only current page and offspring
page type is reflected in file suffix
allow round trip with zwikiimport
"""

# placeholder
