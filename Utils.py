######################################################################
#  miscellaneous utility methods and functions

from types import *
from string import split,join,find,lower,rfind,atoi,strip,lstrip
import os, re, sys, traceback, math
from urllib import quote, unquote

from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import absattr
import Globals
from OFS.SimpleItem import SimpleItem
import zLOG # LOG,ERROR,INFO,WARNING,BLATHER,DEBUG
from DateTime import DateTime
try: # zope 2.7
    from DateTime import SyntaxError
    DateTimeSyntaxError = SyntaxError()
except ImportError:
    DateTimeSyntaxError = DateTime.SyntaxError
try:
    v = open(os.path.join(SOFTWARE_HOME,'version.txt')).read()
    m = re.match(r'(?i)zope\s*([0-9]+)\.([0-9]+)\.([0-9]+)',v)
    ZOPEVERSION = (int(m.group(1)),int(m.group(2)),int(m.group(3)))
except:
    ZOPEVERSION = (9,9,9) # (cvs)

from Products.ZWiki import __version__
from Defaults import PREFER_USERNAME_COOKIE, PAGE_METADATA, SCROLL_CONTENTS
import Permissions
from LocalizerSupport import _, N_


class Utils:
    """
    Miscellaneous utilities mixin for ZWikiPage.
    """
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
    def checkPermission(self, permission, object):
        return getSecurityManager().checkPermission(permission,object)

    def size(self):
        """
        Give the size of this page's text.
        """
        return len(self.text())

    def cachedSize(self):
        """
        Give the total size of this page's text plus cached render data.
        """
        return self.size() + len(self.preRendered()) + self.cachedDtmlSize()

    def cachedDtmlSize(self):
        """
        Estimate the size of this page's cached DTML parse data.
        """
        strings = flattenDtmlParse(getattr(self,'_v_blocks',''))
        strings = filter(lambda x:type(x)==type(''), strings)
        return len(join(strings,''))

    def summary(self,size=100):
        """
        Give a short summary of this page's content.
        """
        return html_quote(self.text()[:size])

    security.declareProtected(Permissions.View, 'excerptAt')
    def excerptAt(self, expr, size=100, highlight=1):
        """
        Return an excerpt of this page at the first occurence of expr.

        Useful when presenting search results.  Does a straight
        case-insensitive string search, after first removing any *
        wildcard character (this may not agree exactly with the catalog
        index's search). SGML tags are quoted.

        If no match is found or expr is blank, returns an empty string.

        When highlight is true, each match within the excerpt is enclosed
        in a span with class "hit". This is not 100% reliable because of
        html quoting and because we don't handle wildcards.
        
        """
        string = re.sub(r'\*','',expr)
        m = re.search(r'(?i)'+re.escape(string),self.text())
        if m and string:
            middle = (m.start()+m.end())/2
            exstart = max(middle-size/2-1,0)
            exend = min(middle+size/2+1,len(self.text()))
            excerpt = html_quote(self.text()[exstart:exend])
            if highlight:
                excerpt = re.sub(
                    r'(?i)'+re.escape(html_quote(string)),
                    #'<span class="hit">%s</span>' % html_quote(m.group()),
                    # XXX temp
                    '<span class="hit" style="background-color:yellow;font-weight:bold;">%s</span>' % html_quote(m.group()),
                    excerpt)
            return excerpt
        else:
            return ''

    def metadataFor(self,page):
        """
        Make a catalog-brain-like object containing page's principal metadata.

        Given a real page object, this returns a PageBrain which emulates
        a catalog brain object (search result), for use when there is no
        catalog. All PAGE_METADATA fields will be included, plus a few more
        for backwards compatibility with old skin templates.

        Warning: fields such as the parents list may be
        copies-by-reference, and should not be mutated.
        """
        class PageBrain(SimpleItem):
            def __init__(self,obj): self._obj = obj
            def getObject(self): return self._obj
        brain = PageBrain(page)
        for attr in PAGE_METADATA+['page_url','title_or_id']:
            # don't acquire these properties
            # XXX messy.. aq_base won't be present in tests
            setattr(brain, attr,
                    absattr(getattr(getattr(page,'aq_base',page),attr,None)))
            #setattr(brain,attr+'__roles__',None) # not needed ?
        brain.linkTitle = '' #XXX not using now.. leave blank so tests pass
        return brain

    def ensureCompleteMetadataIn(self,brain):
        """
        Ensure brain has all the expected metadata, looking in ZODB if needed.

        This should only happen with catalog brains, where the catalog does not
        have all the metadata Zwiki expects. We can't add fields to catalog brains,
        so in that case we'll return a PageBrain instead.

        If the catalog says eg page id is None, we don't do anything about that;
        we'll return it in the metadata.

        If getObject() returns None (a stale catalog entry), we return None.
        """
        for attr in PAGE_METADATA:
            if not hasattr(brain,attr):
                # incomplete brain - make a PageBrain
                p = brain.getObject()
                if p: return self.metadataFor(p)
                else: return None
        return brain

    security.declareProtected(Permissions.View, 'isZwikiPage')
    def isZwikiPage(self,object):
        return getattr(object,'meta_type',None) == self.meta_type

    security.declareProtected(Permissions.View, 'zwiki_version')
    def zwiki_version(self):
        """
        Return the zwiki product version.
        """
        return __version__

    # expose these darn things for dtml programmers once and for all!
    # XXX security issue ?
    security.declareProtected(Permissions.View, 'htmlquote')
    def htmlquote(self, text):
        return html_quote(text)

    security.declareProtected(Permissions.View, 'htmlunquote')
    def htmlunquote(self, text):
        return html_unquote(text)

    security.declareProtected(Permissions.View, 'urlquote')
    def urlquote(self, text):
        return quote(text)

    security.declareProtected(Permissions.View, 'urlunquote')
    def urlunquote(self, text):
        return unquote(text)

    security.declareProtected(Permissions.View, 'usernameFrom')
    def usernameFrom(self, REQUEST=None):
        """
        Get the best available user id from the current visitor's REQUEST.

        We use the first of:
        - a MAILIN_USERNAME set by mailin.py
        - an authenticated username
        - a zwiki_username cookie
        - the client's IP address

        Or, if PREFER_USERNAME_COOKIE in Defaults.py is true, we'll let
        the cookie take precedence. This means an authenticated user could
        pretend to be someone else by setting the cookie, but it's useful
        for this case: a simple community wiki protected by a single
        common login, multiple users distinguished by their
        zwiki_username.

        We'll find REQUEST ourself if necessary (helps backwards compatibility
        with old skin templates).
        """
        REQUEST = REQUEST or getattr(self,'REQUEST',None)
        if not REQUEST: return ''
        authenticated_name = None
        user = REQUEST.get('AUTHENTICATED_USER')
        if user:
            authenticated_name = user.getUserName()
            if authenticated_name == str(user.acl_users._nobody):
                authenticated_name = None
        cookie_name = REQUEST.cookies.get('zwiki_username',None)
        mailin_name = REQUEST.get('MAILIN_USERNAME',None)
        ip_addr = REQUEST.REMOTE_ADDR
        if PREFER_USERNAME_COOKIE:
            return mailin_name or cookie_name or authenticated_name or ip_addr
        else:
            return mailin_name or authenticated_name or cookie_name or ip_addr

    security.declareProtected(Permissions.View, 'requestHasSomeId')
    def requestHasSomeId(self,REQUEST):
        """
        Check REQUEST has either a non-anonymous user or a username cookie.
        """
        username = self.usernameFrom(REQUEST)
        return (username and username != REQUEST.REMOTE_ADDR)

    def __repr__(self):
        return ("<%s %s at 0x%s>"
                % (self.__class__.__name__, `self.id()`, hex(id(self))[2:]))

    security.declareProtected(Permissions.View, 'page_url')
    def page_url(self):
        """return the url path for this wiki page"""
        return self.wiki_url() + '/' + quote(self.id())

    pageUrl=page_url

    security.declareProtected(Permissions.View, 'wiki_url')
    def wiki_url(self):
        """return the base url path for this wiki"""
        try: return self.folder().absolute_url()
        except (KeyError,AttributeError): return '' # for debugging/testing

    wikiUrl=wiki_url

    def defaultPageUrl(self):
        p = self.defaultPage()
        return (p and p.pageUrl()) or None

    def urlForDtmlPageOrMethod(self,pagename,methodname):
        """
        Return the url of an existing dtml page, or of a method, or None.
        """
        p = self.pageWithName(pagename)
        if p and p.dtmlAllowed() and p.hasDynamicContent(): return p.pageUrl()
        elif methodname: return self.defaultPage().pageUrl()+'/'+methodname
        else: return None

    def urlForPageOrDefault(self,pagename,default=None):
        """
        Return the url of an existing page, or the default.
        """
        p = self.pageWithName(pagename)
        return (p and p.pageUrl()) or default

    # XXX keeping these page names in the skin might be easier for i18n ?
    # but way too cumbersome right now
    security.declareProtected(Permissions.View, 'homeUrl')
    def homeUrl(self):
        return self.urlForPageOrDefault('FrontPage',self.wikiUrl())

    security.declareProtected(Permissions.View, 'contentsUrl')
    def contentsUrl(self):
        """
        Return the url of the SiteMap page or wiki contents method.
        
        We used to put the current page name as a target and scroll there,
        but in a large public wiki that generates a lot of unique
        expensive urls for robots. I'm assuming robots are too dumb
        not to crawl both url#target1 and url#target2.

        Perhaps the contents method could check HTTP_REFERER and do a
        redirect, only if you are a human with a cookie ? brrr, confusing..
        There's something to be said for not having the contents scroll
        out from under you anyhow. Try without it for a bit.
        
        """
        if SCROLL_CONTENTS:
            quotedname = quote(self.pageName())
            if self.pageWithId('SiteMap'): 
                return '%s/SiteMap?here=%s#%s' \
                % (self.wiki_url(),quotedname,quotedname)
            else: 
                return '%s/contents#%s' % (self.page_url(),quotedname)
        else:
            if self.pageWithId('SiteMap'): return self.wikiUrl() + '/SiteMap'
            else: return self.defaultPageUrl() + '/contents'

    security.declareProtected(Permissions.View, 'changesUrl')
    def changesUrl(self):
        return self.urlForDtmlPageOrMethod('RecentChanges','recentchanges')

    security.declareProtected(Permissions.View, 'discussionUrl')
    def discussionUrl(self):
        p = self.pageWithName('GeneralDiscussion')
        return (p and p.pageUrl()) or None

    security.declareProtected(Permissions.View, 'trackerUrl')
    def trackerUrl(self):
        return self.urlForDtmlPageOrMethod('IssueTracker','issuetracker')

    security.declareProtected(Permissions.View, 'filterUrl')
    def filterUrl(self):
        return self.urlForDtmlPageOrMethod('FilterIssues','filterissues')

    security.declareProtected(Permissions.View, 'indexUrl')
    def indexUrl(self):
        return self.urlForDtmlPageOrMethod('AllPages',None) #'allpages')

    security.declareProtected(Permissions.View, 'uploadsUrl')
    def uploadsUrl(self):
        return None #self.urlForDtmlPageOrMethod('UploadsPage','uploads')

    security.declareProtected(Permissions.View, 'preferencesUrl')
    def preferencesUrl(self):
        return self.urlForDtmlPageOrMethod('UserOptions','useroptions')

    security.declareProtected(Permissions.View, 'helpUrl')
    def helpUrl(self):
        return self.urlForPageOrDefault('HelpPage',None)

    security.declareProtected(Permissions.View, 'searchUrl')
    def searchUrl(self):
        return self.urlForDtmlPageOrMethod('SearchPage','searchwiki')

    security.declareProtected(Permissions.View, 'creationTime')
    def creationTime(self):
        """
        Return our creation time as a DateTime, guessing if necessary
        """
        try: return DateTime(self.creation_time)
        except (AttributeError,DateTimeSyntaxError):
            return DateTime('2001/1/1')

    security.declareProtected(Permissions.View, 'lastEditTime')
    def lastEditTime(self):
        """
        Return our last edit time as a DateTime, guessing if necessary
        """
        try: return DateTime(self.last_edit_time)
        except (AttributeError,DateTimeSyntaxError):
            return DateTime('2001/1/1')

    security.declareProtected(Permissions.View, 'folder')
    def folder(self):
        """
        return this page's containing folder

        We used to use self.aq_parent everywhere, now
        self.aq_inner.aq_parent to ignore acquisition paths.
        Work for pages without a proper acquisition wrapper too.
        """
        return getattr(getattr(self,'aq_inner',self),'aq_parent',None)

    security.declareProtected(Permissions.View, 'age')
    def age(self):
        """
        return a string describing the approximate age of this page
        """
        return self.asAgeString(self.creation_time)

    security.declareProtected(Permissions.View, 'lastEditInterval')
    def ageInDays(self):
        """
        return the number of days since page creation
        """
        return int(self.getPhysicalRoot().ZopeTime() -
                   self.creationTime())

    security.declareProtected(Permissions.View, 'lastEditInterval')
    def lastEditInterval(self):
        """
        return a string describing the approximate interval since last edit
        """
        return self.asAgeString(self.last_edit_time)

    security.declareProtected(Permissions.View, 'lastEditInterval')
    def lastEditIntervalInDays(self):
        """
        return the number of days since last edit
        """
        return int(self.getPhysicalRoot().ZopeTime() -
                   self.lastEditTime())

    security.declareProtected(Permissions.View, 'asAgeString')
    def asAgeString(self,time):
        """
        return a string describing the approximate elapsed period since time

        time may be a DateTime or suitable string. Returns a blank string
        if there was a problem. Based on the dtml version in ZwikiTracker.
        """
        if not time:
            return 'some time'
        if type(time) is StringType:
            time = DateTime(time)
        # didn't work on a page in CMF, perhaps due to skin acquisition magic
        #elapsed = self.ZopeTime() - time
        elapsed = self.getPhysicalRoot().ZopeTime() - time
        hourfactor=0.041666666666666664
        minutefactor=0.00069444444444444447
        secondsfactor=1.1574074074074073e-05
        days=int(math.floor(elapsed))
        weeks=days/7
        months=days/30
        years=days/365
        hours=int(math.floor((elapsed-days)/hourfactor))
        minutes=int(math.floor((elapsed-days-hourfactor*hours)/minutefactor))
        seconds=int(round((
            elapsed-days-hourfactor*hours-minutefactor*minutes)/secondsfactor))
        if years:
            s = "%d year%s" % (years, years > 1 and 's' or '')
        elif months:
            s = "%d month%s" % (months, months > 1 and 's' or '')
        elif weeks:
            s = "%d week%s" % (weeks, weeks > 1 and 's' or '')
        elif days:
            s = "%d day%s" % (days, days > 1 and 's' or '')
        elif hours:
            s = "%d hour%s" % (hours, hours > 1 and 's' or '')
        elif minutes:
            s = "%d minute%s" % (minutes, minutes > 1 and 's' or '')
        else:
            s = "%d second%s" % (seconds, seconds > 1 and 's' or '')
        return s

Globals.InitializeClass(Utils)


# generic utilities
def BLATHER(*args):
    tmp = []
    for arg in args: tmp.append(str(arg))
    zLOG.LOG('ZWiki',zLOG.BLATHER,' '.join(tmp))

def formattedTraceback():
    type,val,tb = sys.exc_info()
    try:     return join(traceback.format_exception(type,val,tb),'')
    finally: del tb  # Clean up circular reference, avoid IssueNo0536

from cgi import escape
def html_quote(s): return escape(str(s))
def html_unquote(s,
                 character_entities=(
                       (('&amp;'),    '&'),
                       (('&lt;'),    '<' ),
                       (('&gt;'),    '>' ),
                       (('&lt;'), '\213' ),
                       (('&gt;'), '\233' ),
                       (('&quot;'),    '"'))): #"
        text=str(s)
        for re,name in character_entities:
            if find(text, re) >= 0: text=join(split(text,re),name)
        return text

def stringBefore(pattern, str):
    m = re.search(pattern,str)
    if m: return str[:m.start()]
    else: return str

def stringBeforeAndIncluding(pattern, str):
    m = re.search(pattern,str)
    if m: return str[:m.end()]
    else: return str

def stringAfter(pattern, str):
    m = re.search(pattern,str)
    if m: return str[m.end():]
    else: return ''

def stringAfterAndIncluding(pattern, str):
    m = re.search(pattern,str)
    if m: return str[m.start():]
    else: return ''

#def flatten(seq):
#  """
#  Translate a nested sequence into a flat list of string-terminals.
#  We omit duplicates terminals in the process.
#  """
#  got = []
#  pending = [seq]
#  while pending:
#    cur = pending.pop(0)
#    if type(cur) == StringType:
#      if cur not in got:
#        got.append(cur)
#    else:
#      pending.extend(cur)
#  return got

def flatten(recursiveList):
    """
    Flatten a recursive list/tuple structure.
    """
    flatList = []
    for i in recursiveList:
        if type(i) in (ListType,TupleType): flatList.extend(flatten(list(i)))
        else: flatList.append(i)
    return flatList

flatten2 = lambda l,f=lambda L,F : type(L) != type([]) and [L] or reduce(lambda a,b,F=F : a + F(b,F), L, []) :f(l,f)

## flatten from WFN
#def flatten3(seq):
#  """Translate a nested sequence into a flat list of string-terminals.
#  We omit duplicates terminals in the process."""
#  got = []
#  pending = [seq]
#  while pending:
#    cur = pending.pop(0)
#    if type(cur) == StringType:
#      if cur not in got:
#        got.append(cur)
#    else:
#      pending.extend(cur)
#  return got

def flattenDtmlParse(i):
    """
    Roughly flatten a DTML parse structure, for estimating it's size.
    """
    flatList = []
    if type(i) in (ListType,TupleType):
        if len(i) > 0: flatList.extend(flattenDtmlParse(i[0]))
        if len(i) > 1: flatList.extend(flattenDtmlParse(i[1:]))
    elif hasattr(i,'section'):
        flatList.extend(flattenDtmlParse(i.section))
    elif hasattr(i,'im_self'):
        flatList.extend(flattenDtmlParse(i.im_self))
    else:
        flatList.append(i)
    return flatList

# Boldly taken from tres seaver's PTK code.
# Then lifted from ken manheimer's WFN code.
def parseHeadersBody( body, headers=None ):
    """
    Parse any leading 'RFC-822'-ish headers from an uploaded
    document, returning a tuple containing the headers in a dictionary
    and the stripped body.

    E.g.::

        Title: Some title
        Creator: Tres Seaver
        Format: text/plain
        X-Text-Format: structured

        Overview

        This document .....

    would be returned as::

        { 'Title' : 'Some title'
        , 'Creator' : 'Tres Seaver'
        , 'Format' : 'text/plain'
        , 'text_format': 'structured'
        }

    as the headers, plus the body, starting with 'Overview' as
    the first line (the intervening blank line is a separator).

    Allow passing initial dictionary as headers.
    """
    cr = re.compile( '^.*\r$' )
    lines = map( lambda x, cr=cr: cr.match( x ) and x[:-1] or x
               , split( body, '\n' ) )

    i = 0
    if headers is None:
        headers = {}
    else:
        headers = headers.copy()

    hdrlist = []
    for line in lines:
        if line and line[-1] == '\r':
            line = line[:-1]
        if not line:
            break
        tokens = split( line, ':' )
        if len( tokens ) > 1:
            hdrlist.append( ( tokens[0], join( tokens[1:], ':' ) ) )
        elif i == 0:
            return headers, body     # no headers, just return those passed in.
        else:    # continuation
            last, hdrlist = hdrlist[ -1 ], hdrlist[ :-1 ]
            hdrlist.append( ( last[ 0 ]
                            , join( ( last[1], lstrip( line ) ), '\n' )
                            ) )
        i = i + 1

    for hdr in hdrlist:
        headers[ hdr[0] ] = hdr[ 1 ]

    return headers, join( lines[ i+1: ], '\n' )

#from python FAQ:
import tempfile
import os
class Popen3:
    """
    This is a deadlock-safe version of popen, that returns
    an object with errorlevel, out (a string) and err (a string).
    (capturestderr may not work under windows.)
    Example: print Popen3('grep spam','\n\nhere spam\n\n').out
    """
    def __init__(self,command,input='',capturestderr=0):
        outfile=tempfile.mktemp()
        command="( %s ) > %s" % (command,outfile)
        if input:
            infile=tempfile.mktemp()
            open(infile,"w").write(input)
            command=command+" <"+infile
        if capturestderr:
            errfile=tempfile.mktemp()
            command=command+" 2>"+errfile
        self.errorlevel=os.system(command) >> 8
        self.out=open(outfile,"r").read()
        os.remove(outfile)
        if input:
            os.remove(infile)
        if capturestderr:
            self.err=open(errfile,"r").read()
            os.remove(errfile)

def stripList(lines):
    """
    Strip whitespace elements from a list of strings, such as a lines property.

    Accept a list or tuple, return a list. (Zope 2.7 props are tuples.)
    """
    return filter(lambda x:x.strip(),list(lines))
