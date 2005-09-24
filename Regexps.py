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
from Utils import BLATHER, formattedTraceback

# URLs/URIs (better regexps in urllib/urlparse ?)
urlchars = r'[A-Za-z0-9/:;@_%~#=&\.\-\?\+\$,]+'
url      = r'["=]?((about|gopher|http|https|ftp|mailto|file):%s)' % (urlchars)

# valid characters for zwiki page ids
# These are the characters which are used to form safe page ids for both
# free-form names and wiki names.  They are the characters legal in both
# zope ids and urls, excluding _ which we use for quoting. See also
# http://zwiki.org/HowZwikiTitleAndIdWorks . NB it is possible to hack
# zope (OFS.ObjectManager.py bad_id) and adjust the below to enable
# single-byte non-ascii letters in ids, but your urls would be illegal so
# it's probably not worthwhile
zwikiidcharsexpr = re.compile(r'[a-zA-Z0-9.-]')

# used in generating page ids
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
# Zwiki's bare wiki links are standard CamelCase plus the following
# additions:
#
# - words of a single letter are allowed (APage, PageA)
#
# - trailing digits are allowed (PageVersion22, but not Page22Version)
#
# - non-ascii letters defined by the system locale are allowed
#   This means we must include the upper- and lower-case letters for this
#   locale in our regexps. We get them from string.uppercase and
#   string.lowercase, but we need them utf8-encoded since zwiki text is
#   always stored utf8-encoded. So we convert them from the system's
#   default encoding to unicode and re-encode as utf8. It's hard to see
#   how to do this robustly on all systems and it has been the cause of
#   many zwiki startup problems; we must be careful not to let any error
#   stop product initialisation (#769, #1158). Other notes: don't rely on
#   python 2.3's getpreferredencoding, gives wrong answer; work around a
#   python bug with some locales (#392).
#
# - or, a default set of non-ascii letters are allowed if no system locale
#   is configured
#   On systems without a locale configured, we jump through some hoops to
#   support a number of non-ascii letters common in latin and other
#   languages so things are more likely to "just work" for more users.
#
# The aim of this non-ascii stuff is to as far as possible work as
# international users would expect, out of the box and regardless of
# python version, locale setting, platform etc. Better, simpler, more
# robust, more correct ideas are welcome.

# we'll set up the following strings, using the system locale if possible:
# U:  'A|B|C|... '
# L:  'a|b|c|...'
# Ub: '[ABC...]'
# Lb: '[abc...]'
# where A, b etc. are the utf8-encoded upper & lower-case letters.
# Then we'll use them to build the bare wikiname regexps.
#
# For reference, the old non-utf8 regexps were:
#U = string.uppercase
#L = string.lowercase
#wikiname1 = r'(?L)\b[%s]+[%s]+[%s][%s]*[0-9]*' % (U,L,U,U+L)
#wikiname2 = r'(?L)\b[%s][%s]+[%s][%s]*[0-9]*'  % (U,U,L,U+L)
#U = 'A-Z\xc0-\xdf'
#L = 'a-z\xe0-\xff'
#b = '(?<![%s0-9])' % (U+L) # emulate \b
#wikiname1 = r'(?L)%s[%s]+[%s]+[%s][%s]*[0-9]*' % (b,U,L,U,U+L)
#wikiname2 = r'(?L)%s[%s][%s]+[%s][%s]*[0-9]*'  % (b,U,U,L,U+L)

try:
    import locale
    lang, encoding = locale.getlocale()
    encoding = encoding or 'ascii'
    U = '|'.join([c.encode('utf8') for c in unicode(string.uppercase, encoding)])
    L = '|'.join([c.encode('utf8') for c in unicode(string.lowercase, encoding)])
    Ubr = '[%s]' % ''.join([c.encode('utf8') for c in unicode(string.uppercase, encoding)])
    Lbr = '[%s]' % ''.join([c.encode('utf8') for c in unicode(string.lowercase, encoding)])
    localesensitive = r'(?L)'
    wordboundary = r'\b'
except:
    # no locale is set or there was a problem detecting it or a problem
    # decoding string.upper/lowercase
    BLATHER('the system locale gave a problem in Regexps.py, so bare WikiNames will not be locale-aware (traceback follows)\n%s' % formattedTraceback())
    # define a useful default set of non-ascii letters to recognize even
    # with no locale configured, mainly european letters from
    # http://zwiki.org/InternationalCharacterExamples
    # XXX more have been added to that page (latvian, polish).. how far
    # should we go with this ?  Could we make it recognise all non-ascii
    # letters regardless of locale ?  Are regexps getting slow ?
    uppercase = string.uppercase + '\xc3\x80\xc3\x81\xc3\x82\xc3\x83\xc3\x84\xc3\x85\xc3\x86\xc3\x88\xc3\x89\xc3\x8a\xc3\x8b\xc3\x8c\xc3\x8d\xc3\x8e\xc3\x8f\xc3\x92\xc3\x93\xc3\x94\xc3\x95\xc3\x96\xc3\x98\xc3\x99\xc3\x9a\xc3\x9b\xc3\x9c\xc3\x9d\xc3\x87\xc3\x90\xc3\x91\xc3\x9e'
    lowercase = string.lowercase + '\xc3\xa0\xc3\xa1\xc3\xa2\xc3\xa3\xc3\xa4\xc3\xa5\xc3\xa6\xc3\xa8\xc3\xa9\xc3\xaa\xc3\xab\xc3\xac\xc3\xad\xc3\xae\xc3\xaf\xc3\xb2\xc3\xb3\xc3\xb4\xc3\xb5\xc3\xb6\xc3\xb8\xc3\xb9\xc3\xba\xc3\xbb\xc3\xbc\xc3\xbd\xc3\xbf\xc2\xb5\xc3\x9f\xc3\xa7\xc3\xb0\xc3\xb1\xc3\xbe'
    U='|'.join([c.encode('utf8') for c in unicode(uppercase,'utf-8')])
    L='|'.join([c.encode('utf8') for c in unicode(lowercase,'utf-8')])
    Ubr = '[%s]' % ''.join([c.encode('utf8') for c in unicode(uppercase,'utf-8')])
    Lbr = '[%s]' % ''.join([c.encode('utf8') for c in unicode(lowercase,'utf-8')])
    localesensitive = ''
    # make \b a little more accurate with the above
    # XXX needs work, see links at  http://zwiki.org/InternationalCharactersInPageNames
    wordboundary = '(?<![A-Za-z0-9\x80-\xff])' 

# the basic bare wikiname regexps
wikiname1 = r'%s%s(?:%s)+(?:%s)+(?:%s)(?:%s|%s)*[0-9]*' % (localesensitive,wordboundary,U,L,U,U,L)
wikiname2 = r'%s%s(?:%s)(?:%s)+(?:%s)(?:%s|%s)*[0-9]*'  % (localesensitive,wordboundary,U,U,L,U,L)

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
                   
wikilink         = r'!?(%s|%s|%s|%s)' % (wikiname4,bracketedexpr,url,hashnumberexpr)
localwikilink1   = r'(?:%s|%s|%s)' % (wikiname4,bracketedexpr,hashnumberexpr)
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

# and if you're still not having fun, here's one badass regexp:

# sgml tags, including tags containing dtml & python expressions and multiline
# XXX needs more work, does not match all tags.. but usually good enough
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
    simpletagchars = r'[%s0-9\.\=\'\"\:\/\-\#\+\s\*\;\!\&\-]' % StructuredText.STletters.letters
except AttributeError: # older zope
    simpletagchars = r'[A-z0-9\.\=\'\"\:\/\-\#\+\s\*\;\!\&\-]'
dtmltag = r'(?si)<[-/! ]*dtml((".*?")|[^">]+(?![^">]))*>'
dtmlentity = r'(?i)&dtml.*?;'
#simplesgmltag = r'<((".*?")|%s+)>' % simpletagchars
simplesgmltag = r'<((".*?")|(%s)|%s+(?!%s))>' % (dtmltag,simpletagchars,simpletagchars)
dtmlorsgmlexpr = r'(%s|%s|%s)' % (dtmltag,simplesgmltag,dtmlentity)


# From_ separator used to recognize rfc2822 messages - regexp from mailbox.py
# used in Comments.py
fromlineexpr = r'(?m)(?:^|\n\n)From \s*[^\s]+\s+\w\w\w\s+\w\w\w\s+\d?\d\s+\d?\d:\d\d(:\d\d)?(\s+[^\s]+)?\s+\d\d\d\d\s*$'

# purple numbers NIDs XXX should be in purplenumbers plugin ?
nidexpr = r'\s*({nid (?P<nid>[0-9A-z]+?)})'

