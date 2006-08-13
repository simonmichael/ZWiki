# Experimental extension of StructuredText to handle WikiLinks and other Wiki
# extensions, and Latex

import re, locale, string
from StructuredText import HTMLWithImages
from StructuredText.DocumentClass import StructuredTextMarkup
from StructuredText.HTMLWithImages import HTMLWithImages
from StructuredText.DocumentWithImages import DocumentWithImages
#from Products.ZWiki.Regexps import *  # sucks in pieces of zope, and fails.

# URLs/URIs (better regexps in urllib/urlparse ?)
urlchars         = r'[A-Za-z0-9/:;@_%~#=&\.\-\?\+\$,]+'
url              = r'["=]?((about|gopher|http|https|ftp|mailto|file):%s)' % \
                   (urlchars)
bracketedexpr    = r'\[\[?([^\n\]]+)\]\]?'
doublebracketedexpr = r'\[\[([^\n\]]+)\]\]'
zwikiidcharsexpr = re.compile(r'[a-zA-Z0-9.-]')
spaceandlowerexpr = re.compile(r'\s+([%s])'%(string.lowercase))
try:
    lang, encoding = locale.getlocale()
except ValueError:
    lang, encoding = None, None
if encoding:
    try:
        uppercase_uc = unicode(string.uppercase,encoding)
        lowercase_uc = unicode(string.lowercase,encoding)
    except LookupError:
        uppercase_uc = unicode(string.uppercase)
        lowercase_uc = unicode(string.lowercase)
        BLATHER('Warning: unicode() LookupError for encoding %s, WikiNames will not use the system locale' % encoding)
    U = '|'.join([x.encode('utf8') for x in uppercase_uc])
    L = '|'.join([x.encode('utf8') for x in lowercase_uc])
    wikiname1 = r'(?L)\b(?:%s)+(?:%s)+(?:%s)(?:%s|%s)*[0-9]*' % (U,L,U,U,L)
    wikiname2 = r'(?L)\b(?:%s)(?:%s)+(?:%s)(?:%s|%s)*[0-9]*'  % (U,U,L,U,L)
else:
    uppercase = string.uppercase + \
        '\xc3\x80\xc3\x81\xc3\x82\xc3\x83\xc3\x84\xc3\x85\xc3\x86\xc3\x88\xc3\x89\xc3\x8a\xc3\x8b\xc3\x8c\xc3\x8d\xc3\x8e\xc3\x8f\xc3\x92\xc3\x93\xc3\x94\xc3\x95\xc3\x96\xc3\x98\xc3\x99\xc3\x9a\xc3\x9b\xc3\x9c\xc3\x9d\xc3\x87\xc3\x90\xc3\x91\xc3\x9e'
    lowercase = string.lowercase + \
        '\xc3\xa0\xc3\xa1\xc3\xa2\xc3\xa3\xc3\xa4\xc3\xa5\xc3\xa6\xc3\xa8\xc3\xa9\xc3\xaa\xc3\xab\xc3\xac\xc3\xad\xc3\xae\xc3\xaf\xc3\xb2\xc3\xb3\xc3\xb4\xc3\xb5\xc3\xb6\xc3\xb8\xc3\xb9\xc3\xba\xc3\xbb\xc3\xbc\xc3\xbd\xc3\xbf\xc2\xb5\xc3\x9f\xc3\xa7\xc3\xb0\xc3\xb1\xc3\xbe'
    U='|'.join([x.encode('utf8') for x in unicode(uppercase,'utf-8')])
    L='|'.join([x.encode('utf8') for x in unicode(lowercase,'utf-8')])
    b = '(?<![A-Za-z0-9\x80-\xff])' 
    wikiname1 = r'%s(?:%s)+(?:%s)+(?:%s)(?:%s|%s)*[0-9]*' % (b,U,L,U,U,L)
    wikiname2 = r'%s(?:%s)(?:%s)+(?:%s)(?:%s|%s)*[0-9]*'  % (b,U,U,L,U,L)

wikiname3        = r'(?:%s|%s)' % (wikiname1, wikiname2)
wikiname4        = r'(?:(?<!&)%s(?![%s])|(?<=&)%s(?![%s;]))' \
                   % (wikiname3, U+L, wikiname3, U+L)
wikiname         = r'(?<!!)(%s)' %(wikiname4)
wikilink         = r'(?<!!)(%s|%s|%s)' % (wikiname4,bracketedexpr,url)
localwikilink1   = r'(?:%s|%s)' % (wikiname4,bracketedexpr)
localwikilink    = r'(?<!!)(%s)' % (localwikilink1)
interwikilink    = r'(?<!!)((?P<local>%s):(?P<remote>%s))' \
                   % (localwikilink1, urlchars)
anywikilinkexpr  = re.compile(r'(%s|%s)' % (interwikilink,wikilink))
markedwikilinkexpr  = re.compile(r'<zwiki>(.*?)</zwiki>')
untitledwikilinkexpr = \
          re.compile(r'<a href="([^"/]*/)*(?P<page>[^/"]*)" title="">.*?</a>')
remotewikiurl    = r'(?mi)RemoteWikiURL[:\s]*(?P<remoteurl>[^\s]+)\s*$'
protected_line   = r'(?m)^!(.*)$'
footnoteexpr     = r'(?sm)^\.\. \[([^\n\]]+)\]'
javascriptexpr   = r'(?iL)<(([^>\w]*script|iframe)[^>]*)>' # \1 will be displayed
htmlheaderexpr = r'(?si)^(\s*<!doctype.*?)?\s*<html.*?<body.*?>'
htmlfooterexpr = r'(?si)</body.*?>\s*</html.*?>\s*$'
try: # work with different zope versions                                  
    # copied from doc_sgml()
    import StructuredText
    simpletagchars = \
      r'[%s0-9\.\=\'\"\:\/\-\#\+\s\*\;\!\&\-]' % StructuredText.STletters.letters
except AttributeError: # older zope
    simpletagchars = r'[A-z0-9\.\=\'\"\:\/\-\#\+\s\*\;\!\&\-]'
dtmltag = r'(?si)<[-/! ]*dtml((".*?")|[^">]+(?![^">]))*>'
dtmlentity = r'(?i)&dtml.*?;'
simplesgmltag = r'<((".*?")|(%s)|%s+(?!%s))>' % (dtmltag,simpletagchars,simpletagchars)
dtmlorsgmlexpr = r'(%s|%s|%s)' % (dtmltag,simplesgmltag,dtmlentity)
fromlineexpr = r'(?m)(?:^|\n\n)From \s*[^\s]+\s+\w\w\w\s+\w\w\w\s+\d?\d\s+\d?\d:\d\d(:\d\d)?(\s+[^\s]+)?\s+\d\d\d\d\s*$'
nidexpr = r'\s*({nid (?P<nid>[0-9A-z]+?)})'

class WikiLink(StructuredTextMarkup):
    """ Represents a WikiLink or [Wiki Link] """

class WikiDocumentClass(DocumentWithImages):
    text_types = [ 'doc_wikilink' ] + DocumentWithImages.text_types

    def doc_wikilink(self,s,expr=anywikilinkexpr.search):
        r = expr(s)
        if r:
            start,end = r.span()
            text = s[start:end]
            return (WikiLink(text),start,end)
        return None

ets = HTMLWithImages.element_types
ets.update({'WikiLink': 'wikilink'})

class ZWikiHTML(HTMLWithImages):
    element_types = ets
    def wikilink(self, doc, level, output):
        output("<dtml-var expr=\"wikilink('%s')\">" % doc.getNodeValue())






