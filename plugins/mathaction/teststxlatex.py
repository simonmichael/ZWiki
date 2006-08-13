#!/usr/bin/python2.2

import sys, os
sys.path.insert(0,'/usr/lib/zope/lib/python')
sys.path.insert(0,os.getcwd)

from StructuredText.ST import StructuredText
from StructuredTextLatex import ZWikiHTML, WikiDocumentClass

parser = ZWikiHTML()
docclass = WikiDocumentClass()

def HTML(text):
    st = StructuredText(text)
    doc = docclass(st);
    return parser(doc,header=0)

print HTML("WikiName")
print HTML("[Wiki Name]")
print HTML("![Escaped Wiki Name]")
print HTML('"blah":http://blah.org')
print HTML('This is ref[1]. and more\n\n\n.. [1] foo')

