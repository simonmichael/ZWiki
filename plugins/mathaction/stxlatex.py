#!/usr/bin/python

import sys
#from StructuredText import HTMLClass
sys.path.append('/usr/lib/zope/lib/python')
from StructuredText import ST
from StructuredText import DocumentClass
from StructuredText import ClassicDocumentClass
from StructuredText import StructuredText
from StructuredText import HTMLClass
from StructuredText.StructuredText import HTML
import os, unittest, cStringIO
from types import UnicodeType
from OFS import ndiff

#print ST.StructuredText('* asdf\n\n* jkl\n')
print HTML('<img src="asdf" alt="** asdf **">')
print HTML('**asdf**')
print HTML("<!-- **asdf** -->")
print HTML("""
<img src="images/gear_anim.gif" alt="** test **">

Bug check: StructuredText marks up things inside HTML comments.  :(  <!-- **test** -->
""")

# Inherit DocumentClass to do parsing
#   add 'doc_latex', 'doc_wikilink' to text_types
# Copy (or inherit) HTMLClass to do rendering
# Likewise copy HTMLClass to do LaTeX rendering.
