######################################################################
# regular expressions used by Zwiki
#
# Some people, when confronted with a problem, think 'I know, I'll use
# regular expressions.' Now they have two problems. --Jamie Zawinski
#
# Be brave. Read on.
#
# don't bother trying to keep to 80 char lines, here

import re, string

import Defaults
from Utils import BLATHER, DEBUG, formattedTraceback

# URLs/URIs (better regexps in urllib/urlparse ?)
urlchars = r'[A-Za-z0-9/:;@_%~#=&\.\-\?\+\$,]+'
url      = r'["=]?((about|gopher|http|https|ftp|mailto|file):%s)' % (urlchars)

# valid characters for zwiki page ids
# These are the characters which are used to form the ids of zwiki page
# objects.  They must be legal in both zope ids and urls, and exclude _
# which is used for quoting. Cf http://zwiki.org/HowZwikiTitleAndIdWorks .
# It is possible to enable single-byte non-ascii letters in page ids here
# if you also hack bad_id in zope's OFS/ObjectManager.py, but then your
# urls would be illegal.
zwikiidcharsexpr = re.compile(r'[a-zA-Z0-9.-]')

# used in generating page ids
# XXX NB this is affected by locale - may not be what we want
spaceandlowerexpr = re.compile(r'\s+([%s])'%(string.lowercase))

# free-form wiki links
# zwiki uses three kinds of delimiters to enclose free-form wiki page names:

# single bracketed phrases (only) [...]
# what's inside the brackets should be group 1
singlebracketedexpr = r'\[(?:(?!\[))([^\n\]]+)\]'

# wikipedia-style double brackets [[...]]
doublebracketedexpr = r'\[\[([^\n\]]+)\]\]'

# wicked-style double parentheses ((...)), for international users whose
# keyboards make brackets hard to type
doubleparenthesisexpr = r'\(\(([^\n\]]+)\)\)'

# match either single or double brackets, to simplify later regexps a little
bracketedexpr       = r'\[\[?([^\n\]]+)\]\]?'

# bare wikinames
#
# "bare wikinames" here means page names which will be automatically
# wiki-linked without needing to be enclosed in brackets. Zwiki's
# wikinames are standard c2.com-style CamelCase plus the following
# additions:
#
# - words of a single letter are allowed (APage, PageA)
#
# - trailing digits are allowed (PageVersion22, but not Page22Version)
#   (XXX for simplicity and to reduce unexpected wikilinking, eg of big
#   random texts. Change this ?)
#
# - non-ascii letters are allowed. We aim to as far as possible work as
#   international users would expect, out of the box and regardless of
#   python version, locale setting, platform etc. Better ideas are
#   welcome. One of two possible setups is chosen at startup:
#
#   1. if a system locale is configured, the locale's letters are allowed
#
#      We include these in our regexps below. We need them utf8-encoded
#      since zwiki text is always stored utf8-encoded. So we convert them
#      from the system's default encoding to unicode and re-encode as
#      utf8.  It's hard to see how to do this robustly on all systems and
#      it has been the cause of many zwiki startup problems, so we must be
#      careful not to let any error stop product initialisation (#769,
#      #1158). Other notes: don't rely on python 2.3's
#      getpreferredencoding, gives wrong answer; work around a python bug
#      with some locales (#392).
#
#   2. if no system locale is configured or there was an error during the
#      above, a default set of non-ascii letters are allowed
#
#      On systems where we can't detect the locale's characters, we jump
#      through some hoops to support a number of non-ascii letters common
#      in latin and other languages so things are more likely to "just
#      work" for more users.

# we'll set up the following strings to use when building the regexps:
# U:   'A|B|C|... '
# L:   'a|b|c|...'
# Ubr: '[ABC...]'
# Lbr: '[abc...]'
# where A, b etc. are the utf8-encoded upper & lower-case letters.
try:
    import locale
    lang, encoding = locale.getlocale()
    U =           '|'.join([c.encode('utf8') for c in unicode(string.uppercase, encoding)])
    L =           '|'.join([c.encode('utf8') for c in unicode(string.lowercase, encoding)])
    Ubr = '[%s]' % ''.join([c.encode('utf8') for c in unicode(string.uppercase, encoding)])
    Lbr = '[%s]' % ''.join([c.encode('utf8') for c in unicode(string.lowercase, encoding)])
    relocaleflag = r'(?L)'
    wordboundary = r'\b'
except:
    # no locale is set, or there was a problem detecting it or a
    # problem decoding its letters.
    # XXX must be a less ugly way to do this:
    # if it's just that there's no locale, don't log a warning
    try: lang, encoding = locale.getlocale()
    except: lang, encoding = -1,-1
    if (lang, encoding) == (None, None): pass
    else:
        BLATHER('the system locale gave a problem in Regexps.py, so WikiNames will not be locale-aware')
        DEBUG(formattedTraceback())
    # define a useful default set of non-ascii letters, mainly european letters
    # from http://zwiki.org/InternationalCharacterExamples
    # XXX more have been added to that page (latvian, polish).. how far
    # should we go with this ?  Could we make it always recognise all
    # letters and forget locale awareness ?  Are regexps getting slow ?
    # XXX needs more work, see failing links at
    # http://zwiki.org/InternationalCharactersInPageNames
    uppercase = string.uppercase + '\xc3\x80\xc3\x81\xc3\x82\xc3\x83\xc3\x84\xc3\x85\xc3\x86\xc3\x88\xc3\x89\xc3\x8a\xc3\x8b\xc3\x8c\xc3\x8d\xc3\x8e\xc3\x8f\xc3\x92\xc3\x93\xc3\x94\xc3\x95\xc3\x96\xc3\x98\xc3\x99\xc3\x9a\xc3\x9b\xc3\x9c\xc3\x9d\xc3\x87\xc3\x90\xc3\x91\xc3\x9e'
    lowercase = string.lowercase + '\xc3\xa0\xc3\xa1\xc3\xa2\xc3\xa3\xc3\xa4\xc3\xa5\xc3\xa6\xc3\xa8\xc3\xa9\xc3\xaa\xc3\xab\xc3\xac\xc3\xad\xc3\xae\xc3\xaf\xc3\xb2\xc3\xb3\xc3\xb4\xc3\xb5\xc3\xb6\xc3\xb8\xc3\xb9\xc3\xba\xc3\xbb\xc3\xbc\xc3\xbd\xc3\xbf\xc2\xb5\xc3\x9f\xc3\xa7\xc3\xb0\xc3\xb1\xc3\xbe'
    U =           '|'.join([c.encode('utf8') for c in unicode(uppercase,'utf-8')])
    L =           '|'.join([c.encode('utf8') for c in unicode(lowercase,'utf-8')])
    Ubr = '[%s]' % ''.join([c.encode('utf8') for c in unicode(uppercase,'utf-8')])
    Lbr = '[%s]' % ''.join([c.encode('utf8') for c in unicode(lowercase,'utf-8')])
    relocaleflag = ''
    wordboundary = '(?<![A-Za-z0-9\x80-\xff])' 

# the basic bare wikiname regexps
# ?: means "don't remember", apparently a performance optimization
wikiname1 = r'%s%s(?:%s)+(?:%s)+(?:%s)(?:%s|%s)*[0-9]*' % (relocaleflag,wordboundary,U,L,U,U,L)
wikiname2 = r'%s%s(?:%s)(?:%s)+(?:%s)(?:%s|%s)*[0-9]*'  % (relocaleflag,wordboundary,U,U,L,U,L)

# are we having fun yet ?

# don't match things like &RightArrow;
# could also do this in markLinksIn and make it per-pagetype ?
wikiname3        = r'(?:%s|%s)' % (wikiname1, wikiname2)

# is there a reason for the following regexp ?
# I think no ampersand before or an ampersand but no char/; behind is enough
# cautiously commented  --StefanRank
# more trouble: the XML spec also allows &---WikiName---;
#wikiname4        = r'(?:(?<!&)%s|(?<=&)%s(?![%s;]))' % (wikiname3, wikiname3, U+L)
wikiname4        = r'(?:(?<!&)%s(?![%s])|(?<=&)%s(?![%s;]))' % (wikiname3, U+L, wikiname3, U+L)

wikiname         = r'!?(%s)' %(wikiname4)

# issue number links XXX should be in the tracker plugin ?
simplehashnumber = r'\#[0-9]+'
# avoid html entities like &#123;
hashnumberexpr   = r'(?:(?<!&)%s|(?<=&)%s(?![0-9;]))' % (simplehashnumber, simplehashnumber)
                   
wikilink         = r'!?(%s|%s|%s|%s|%s)' % (wikiname4,bracketedexpr,doubleparenthesisexpr,url,hashnumberexpr)
localwikilink1   = r'(?:%s|%s|%s|%s)' % (wikiname4,bracketedexpr,doubleparenthesisexpr,hashnumberexpr)
localwikilink    = r'!?(%s)' % (localwikilink1)
interwikilink    = r'!?((?P<local>%s):(?P<remote>%s))' % (localwikilink1,urlchars)
anywikilinkexpr  = re.compile(r'(%s|%s)' % (interwikilink,wikilink))
markedwikilinkexpr  = re.compile(r'<zwiki>(.*?)</zwiki>')
untitledwikilinkexpr = re.compile(r'<a href="([^"/]*/)*(?P<page>[^/"]*)" title="">.*?</a>')
wikinamewords    = r'((%s(?!%s))+|%s%s+|[0-9]+)'%(Ubr,Lbr,Ubr,Lbr)
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

# one more badass regexp:
# sgml tags, including ones containing dtml & python expressions and multiline
# Notes:
# - r'(?s)<((".*?")|[^">]+)*>' takes exponential time
# - r'(?s)<((".*?")|[^">]+(?![^">]))*>' avoids backtracking (see perlre)
# - to avoid matching casual angle bracket use, treat dtml separately
# - recognising that stuff like <!-- dtml-var ...> & </dtml ...> is also dtml
# - and that a simple sgml tag may contain a dtml tag
# - put dtml pattern first, longest match does not apply with (|) I think
# - not perfect, but seems to match everything in practice
dtmlentity =     r'(?i)&dtml.*?;'
dtmltag =        r'(?si)<[-/! ]*dtml((".*?")|[^">]+(?![^">]))*>'
tagchars =       r'[%s0-9\.\=\'\"\:\/\-\#\+\s\*\;\!\&\-]' % string.letters
sgmltag =        r'<((".*?")|(%s)|%s+(?!%s))>' % (dtmltag,tagchars,tagchars)
dtmlorsgmlexpr = r'(%s|%s|%s)' % (dtmltag,sgmltag,dtmlentity)


# From_ separator used to recognize rfc2822 messages - regexp from mailbox.py
# used in Comments.py
fromlineexpr = r'(?m)(?:^|\n\n)From \s*[^\s]+\s+\w\w\w\s+\w\w\w\s+\d?\d\s+\d?\d:\d\d(:\d\d)?(\s+[^\s]+)?\s+\d\d\d\d\s*$'

# purple numbers NIDs XXX should be in purplenumbers plugin ?
nidexpr = r'\s*({nid (?P<nid>[0-9A-z]+?)})'

