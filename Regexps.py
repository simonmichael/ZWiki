######################################################################
# regular expressions used by ZWiki
#
# Some people, when confronted with a problem, think 'I know, I'll use
# regular expressions.' Now they have two problems. --Jamie Zawinski
#
# Be brave. Read on.

import re, string

import Defaults
from Utils import BLATHER

# URLs/URIs (better regexps in urllib/urlparse ?)
urlchars         = r'[A-Za-z0-9/:;@_%~#=&\.\-\?\+\$,]+'
url              = r'["=]?((about|gopher|http|https|ftp|mailto|file):%s)' % \
                   (urlchars)

# valid characters for zwiki page ids
# These are the characters which are used to form safe page ids for both
# free-form names and wiki names.  They are the characters legal in both
# zope ids and urls, excluding _ which we use for quoting. (See
# canonicalIdFrom).
# You have a choice here -
# 1. Don't allow international characters in ids.
zwikiidcharsexpr = re.compile(r'[a-zA-Z0-9.-]')
# 2. Allow (single-byte) international characters in page ids.
# You also need to hack zope's OFS.ObjectManager.bad_id, eg:
## bad_id = re.compile(r'[^\xC0-\xFFa-zA-Z0-9-_~,.$# ]').search
# what's the thread-safety issue noted there ?
# extract zopeidchars from bad_id - hacky:
#from OFS.ObjectManager import bad_id
#try:
#    zopeidchars = re.sub(r'\^',r'',bad_id.__self__.pattern)
#    zopeidchars = re.sub(r'\\\(',r'(',zopeidchars)
#    zopeidchars = re.sub(r'\\\)',r')',zopeidchars)
#except AttributeError:
#    # older zope uses ts_regex
#    zopeidchars = re.sub(r'\^',r'',bad_id.im_self.givenpat)
#    zopeidchars = re.sub(r'\\\,',r',',zopeidchars)
#    zopeidchars = re.sub(r'\\\.',r'.',zopeidchars)
#zwikiidcharsexpr = re.compile(re.sub(r'[_~,$()# ]',r'',zopeidchars))

# also used in generating page ids
# XXX NB this is affected by locale - may not be what we want
spaceandlowerexpr = re.compile(r'\s+([%s])'%(string.lowercase))

# free-form wiki links
# zwiki uses [...] to link to free-form page names. These can be almost
# anything (on a single line).
# group 1 should be what's inside the brackets
# new: allow wikipedia-style double brackets.. cheat a bit,
# don't require them to be balanced.
bracketedexpr    = r'\[\[?([^\n\]]+)\]\]?'
doublebracketedexpr = r'\[\[([^\n\]]+)\]\]'

# bare wiki links
#
# Zwiki's bare wiki links are standard CamelCase, but also allow words of
# a single letter (APage, PageA) and trailing digits (PageVersion002).
#
# They can also contain international characters defined by your locale,
# or a default set if no locale is defined.
# XXX isn't this limiting ? Can we allow all international characters,
# regardless of locale ? How far should we go ? Are regexps getting slow ?

import locale
# work around a python bug (IssueNo0392)
# don't require python 2.3's getpreferredencoding
try:
    lang, encoding = locale.getlocale()
except ValueError:
    lang, encoding = None, None
    BLATHER('Warning: getlocale() ValueError, WikiNames will not use the system locale')

if encoding:
    # recognize this locale's upper and lower-case characters
    # old single-byte regexps:
    #U = string.uppercase
    #L = string.lowercase
    #wikiname1 = r'(?L)\b[%s]+[%s]+[%s][%s]*[0-9]*' % (U,L,U,U+L)
    #wikiname2 = r'(?L)\b[%s][%s]+[%s][%s]*[0-9]*'  % (U,U,L,U+L)
    # utf-8-aware regexps:
    # XXX work around a python bug (?) (IssueNo0769)
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
    # it looks like no locale is set, or we could not detect it; we'll try
    # to recognize a default set of international characters.
    # In this case we emulate \b and word boundaries may not be quite as
    # accurate.
    # single-byte regexps:
    #U = 'A-Z\xc0-\xdf'
    #L = 'a-z\xe0-\xff'
    #b = '(?<![%s0-9])' % (U+L)
    #wikiname1 = r'(?L)%s[%s]+[%s]+[%s][%s]*[0-9]*' % (b,U,L,U,U+L)
    #wikiname2 = r'(?L)%s[%s][%s]+[%s][%s]*[0-9]*'  % (b,U,U,L,U+L)
    # utf-8.. not so easy..
    # default set includes european chars from InternationalCharacterExamples
    # not latvian, polish, etc. as I don't have a complete list
    # XXX they are there now.. how many chars should we recognize here
    uppercase = string.uppercase + \
        '\xc3\x80\xc3\x81\xc3\x82\xc3\x83\xc3\x84\xc3\x85\xc3\x86\xc3\x88\xc3\x89\xc3\x8a\xc3\x8b\xc3\x8c\xc3\x8d\xc3\x8e\xc3\x8f\xc3\x92\xc3\x93\xc3\x94\xc3\x95\xc3\x96\xc3\x98\xc3\x99\xc3\x9a\xc3\x9b\xc3\x9c\xc3\x9d\xc3\x87\xc3\x90\xc3\x91\xc3\x9e'
    lowercase = string.lowercase + \
        '\xc3\xa0\xc3\xa1\xc3\xa2\xc3\xa3\xc3\xa4\xc3\xa5\xc3\xa6\xc3\xa8\xc3\xa9\xc3\xaa\xc3\xab\xc3\xac\xc3\xad\xc3\xae\xc3\xaf\xc3\xb2\xc3\xb3\xc3\xb4\xc3\xb5\xc3\xb6\xc3\xb8\xc3\xb9\xc3\xba\xc3\xbb\xc3\xbc\xc3\xbd\xc3\xbf\xc2\xb5\xc3\x9f\xc3\xa7\xc3\xb0\xc3\xb1\xc3\xbe'
    U='|'.join([x.encode('utf8') for x in unicode(uppercase,'utf-8')])
    L='|'.join([x.encode('utf8') for x in unicode(lowercase,'utf-8')])
    # can't easily emulate \b.. look-behind must be fixed-width.
    # this should work in a lot of cases:
    #b = '(?<![A-Za-z0-9\x80\x81\x82\x83\x84\x85\x86\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x92\x93\x94\x95\x96\x98\x99\x9a\x9b\x9c\x9d\x87\x90\x91\x9e\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb2\xb3\xb4\xb5\xb6\xb8\xb9\xba\xbb\xbc\xbd\xbf\xc2\xb5\x9f\xa7\xb0\xb1\xbe])' 
    # try this: accept a lot of weird stuff (too much?) as a word boundary:
    b = '(?<![A-Za-z0-9\x80-\xff])' 
    wikiname1 = r'%s(?:%s)+(?:%s)+(?:%s)(?:%s|%s)*[0-9]*' % (b,U,L,U,U,L)
    wikiname2 = r'%s(?:%s)(?:%s)+(?:%s)(?:%s|%s)*[0-9]*'  % (b,U,U,L,U,L)

# are we having fun yet..
# don't match things like &RightArrow;
# could also do this in markLinksIn and make it per-pagetype ?
wikiname3        = r'(?:%s|%s)' % (wikiname1, wikiname2)
wikiname4        = r'(?:(?<!&)%s(?![%s])|(?<=&)%s(?![%s;]))' \
                   % (wikiname3, U+L, wikiname3, U+L)
wikiname         = r'!?(%s)' %(wikiname4)
wikilink         = r'!?(%s|%s|%s)' % (wikiname4,bracketedexpr,url)
localwikilink1   = r'(?:%s|%s)' % (wikiname4,bracketedexpr)
localwikilink    = r'!?(%s)' % (localwikilink1)
interwikilink    = r'!?((?P<local>%s):(?P<remote>%s))' \
                   % (localwikilink1, urlchars)
anywikilinkexpr  = re.compile(r'(%s|%s)' % (interwikilink,wikilink))
markedwikilinkexpr  = re.compile(r'<zwiki>(.*?)</zwiki>')
untitledwikilinkexpr = \
          re.compile(r'<a href="([^"/]*/)*(?P<page>[^/"]*)" title="">.*?</a>')
remotewikiurl    = r'(?mi)RemoteWikiURL[:\s]+(?P<remoteurl>[^\s]*)\s*$'
protected_line   = r'(?m)^!(.*)$'

# stx footnotes 
# handled by us so as to co-exist with our bracketed links
# real stx allows refchars = r'[0-9_%s-]' % (string.letters)
footnoteexpr     = r'(?sm)^\.\. \[([^\n\]]+)\]'

# for stripping javascript
# XXX needs work, eg should not match
# <input... name="ZPythonScriptHTML_editAction:method">
javascriptexpr   = r'(?iL)<(([^>\w]*script|iframe)[^>]*)>' # \1 will be displayed

# for stripping HTML header/footer
# XXX these are expensive, may hit max recursion limit on bsd
htmlheaderexpr = r'(?si)^(\s*<!doctype.*?)?\s*<html.*?<body.*?>'
htmlfooterexpr = r'(?si)</body.*?>\s*</html.*?>\s*$'
# better ? safe ?
htmlbodyexpr = r'(?si)^.*?<body[^>]*?>(.*)</body[^>]*?>.*?$'

# sgml tags, including those containing dtml/python and multi-line
# XXX needs more work, does not match all tags
#
# one badass regexp
#
#r'(?s)<((".*?")|[^">]+)*>'          # takes exponential time
#r'(?s)<((".*?")|[^">]+(?![^">]))*>' # avoids backtracking (see perlre)
# to avoid matching casual angle bracket use, treat dtml separately
# recognizing that stuff like <!-- dtml-var ...> & </dtml ...> is also dtml
# and that a simple sgml tag may contain a dtml tag
# put dtml pattern first, longest match does not apply with (|) I think
try: # work with different zope versions                                  
    # copied from doc_sgml()
    import StructuredText
    simpletagchars = \
      r'[%s0-9\.\=\'\"\:\/\-\#\+\s\*\;\!\&\-]' % StructuredText.STletters.letters
except AttributeError: # older zope
    simpletagchars = r'[A-z0-9\.\=\'\"\:\/\-\#\+\s\*\;\!\&\-]'
dtmltag = r'(?si)<[-/! ]*dtml((".*?")|[^">]+(?![^">]))*>'
dtmlentity = r'(?i)&dtml.*?;'
#simplesgmltag = r'<((".*?")|%s+)>' % simpletagchars
simplesgmltag = r'<((".*?")|(%s)|%s+(?!%s))>' % (dtmltag,simpletagchars,simpletagchars)
dtmlorsgmlexpr = r'(%s|%s|%s)' % (dtmltag,simplesgmltag,dtmlentity)

# From_ separator used to recognize rfc2822 messages - regexp from mailbox.py
# used in Messages.py
fromlineexpr = r'(?m)(?:^|\n\n)From \s*[^\s]+\s+\w\w\w\s+\w\w\w\s+\d?\d\s+\d?\d:\d\d(:\d\d)?(\s+[^\s]+)?\s+\d\d\d\d\s*$'

# NIDs embedded in page source
# used in PurpleNumbers.py
nidexpr = r'\s*({nid (?P<nid>[0-9A-z]+?)})'

