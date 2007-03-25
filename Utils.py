######################################################################
#  miscellaneous utility methods and functions

from types import *
from string import split,join,find,lower,rfind,atoi,strip,lstrip
import os, re, sys, traceback, math
from urllib import quote, unquote

from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import absattr
from Globals import InitializeClass
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
from Defaults import PREFER_USERNAME_COOKIE, PAGE_METADATA, BORING_PAGES
import Permissions
from I18n import _

# adapt to zope 2.9 transaction api
try: from transaction import get as get_transaction
except ImportError: get_transaction = get_transaction

ZWIKI_BIRTHDATE='1999/11/05'

ZWIKIDIR = os.path.dirname(__file__)
def abszwikipath(path): return os.path.join(ZWIKIDIR,path)


class PageUtils:
    """
    Miscellaneous utility methods for zwiki pages.
    """
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')

    ######################################################################
    # misc security utilities
    
    def checkPermission(self, permission, object):
        return getSecurityManager().checkPermission(permission,object)

    # Zwiki implements a little extra access control in addition to Zope's
    # permissions, to allow more lightweight security based on cookies etc.
    def checkSufficientId(self, REQUEST=None):
        REQUEST = REQUEST or getattr(self,'REQUEST',None)
        return (self.requestHasUsername(REQUEST) or
                not getattr(self,'edits_need_username',0))

    # used this in standard templates for while, so must keep it for
    # backwards compatibility. The name is no longer accurate.
    userIsIdentified = checkSufficientId

    def requestHasUsername(self,REQUEST=None):
        """
        Check REQUEST has either an authenticated user or a username cookie.
        """
        REQUEST = REQUEST or getattr(self,'REQUEST',None)
        username = self.usernameFrom(REQUEST)
        return (username and username != REQUEST.REMOTE_ADDR)

    def usernameFrom(self, REQUEST=None, ip_address=1):
        """
        Get the best available user id from the current visitor's REQUEST.

        We use the first of:
        - a MAILIN_USERNAME set by mailin.py
        - an authenticated username
        - a zwiki_username cookie
        - the client's IP address, unless disabled

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
        ip_addr = ip_address and REQUEST.REMOTE_ADDR or ''
        if PREFER_USERNAME_COOKIE:
            return mailin_name or cookie_name or authenticated_name or ip_addr
        else:
            return mailin_name or authenticated_name or cookie_name or ip_addr

    ######################################################################

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

    def summary(self,size=200,paragraphs=1,charset="utf-8"):
        """
        Give a short plaintext summary of this page's content.

        We generate this by excerpting the first paragraph.
        Specifically, we take the page's document part, strip html tags,
        and return up to the specified number of characters or paragraphs,
        replacing the last word with an ellipsis if we had to truncate.
        """
        size, paragraphs = int(size), int(paragraphs)
        t = self.documentPart()
        t = t.decode(charset)  # go to unicode.
        t = re.sub(r'<(?=\S)[^>]+>','',t).strip() # strip html tags
        if paragraphs: t = join(split(t,'\n\n')[:paragraphs],'\n\n')
        if len(t) > size:
            t = t[:size]
            t = re.sub(r'\w*$',r'',t) + '...'
        t = t.encode(charset)  # get back from unicode.
        return html_quote(t)

    def renderedSummary(self,size=500,paragraphs=1):
        """
        Give a summary of this page's content, as rendered html.

        Similar to summary(), but this one tries to apply the page's
        formatting rules and do wiki linking. We remove any enclosing <p>.
        """
        return re.sub(r'(?si)^<p>(.*)</p>\n?$', r'\1',
            self.renderLinksIn(
            self.pageType().format(
            self.summary(size=size, paragraphs=paragraphs))))

    security.declareProtected(Permissions.View, 'excerptAt')
    def excerptAt(self, expr, size=100, highlight=1, text=None):
        """
        Return a highlighted search result excerpt from this page (or text).

        This method searches this page's text, or the provided text, for
        the first occurrence of expr (cleaned up) and returns the
        surrounding text chunk, html quoted, and optionally with the
        matches enclosed in styled spans. If no match is found, it just
        returns a chunk from the beginning.

        It should mimic the search strategy of SearchPage, but that
        depends on catalog configuration and it currently doesn't do a
        very good job, so the excerpts and highlights can be misleading.
        """
        text = text or self.text()
        string = re.sub(r'\*','',expr)
        m = re.search(r'(?i)'+re.escape(string),text)
        if m and string:
            middle = (m.start()+m.end())/2
            exstart = max(middle-size/2-1,0)
            exend = min(middle+size/2+1,len(text))
            excerpt = html_quote(text[exstart:exend])
            if highlight:
                excerpt = re.sub(
                    r'(?i)'+re.escape(html_quote(string)),
                    #'<span class="hit">%s</span>' % html_quote(m.group()),
                    # XXX temp
                    '<span class="hit" style="background-color:yellow;font-weight:bold;">%s</span>' % html_quote(m.group()),
                    excerpt)
            return excerpt
        else:
            return html_quote(text[:size])

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
        class PageBrain(SimpleItem): # XXX why a SimpleItem ?
            def __init__(self,obj): self._obj = obj
            def getObject(self): return self._obj
        brain = PageBrain(page)
        for attr in PAGE_METADATA+['page_url','title_or_id']:
            # protect against import or attr errors when a page type has
            # been uninstalled
            try:
                # don't acquire these properties
                # aq_base won't be present during unit tests.. messy
                setattr(brain, attr,
                        absattr(getattr(getattr(page,'aq_base',page),attr,None)))
            except (ImportError, AttributeError):
                setattr(brain, attr, None)
        #XXX not using now.. leave blank so tests pass
        brain.linkTitle = '' 
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

    def __repr__(self):
        return ("<%s %s at 0x%s>"
                % (self.__class__.__name__, `self.id()`, hex(id(self))[2:]))

    security.declareProtected(Permissions.View, 'pageUrl')
    def pageUrl(self):
        """Return the url for this wiki page."""
        return self.wiki_url() + '/' + quote(self.id())

    page_url=pageUrl

    security.declareProtected(Permissions.View, 'wikiUrl')
    def wikiUrl(self):
        """Return the url for this wiki's folder."""
        try: return self.folder().absolute_url()
        except (KeyError,AttributeError): return '' # for debugging/testing

    wiki_url=wikiUrl

    security.declareProtected(Permissions.View, 'wikiPath')
    def wikiPath(self):
        """Return the path part of this wiki's url.
        """
        # absolute_url_path and virtual_url_path just don't work 
        # in a apache proxy-vhm-zope situation, apparently.
        #try: return self.folder().absolute_url_path()
        try: return re.sub(r'.*?//.*?/',r'/',self.folder().absolute_url())
        except (KeyError,AttributeError): return '' # for debugging/testing

    def defaultPageUrl(self):
        p = self.defaultPage()
        return (p and p.pageUrl()) or ''

    def urlForDtmlPageOrMethod(self,pagename,methodname):
        """
        Return the url of an existing dtml page, or of a method, or ''.
        """
        p = self.pageWithName(pagename)
        if p and p.dtmlAllowed() and p.hasDynamicContent(): return p.pageUrl()
        elif methodname: return self.defaultPage().pageUrl()+'/'+methodname
        else: return ''

    def urlForPageOrDefault(self,pagename,default=''):
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
    def contentsUrl(self, scroll=1):
        """
        Return the url of zwiki's contents method.

        In general, we try to keep these urls stable, so as to minimise
        useless work done for web robots. For the contents page, this was
        tricky because we like it to know what page we were looking at
        (for you are here), and to scroll there. Here's what we do now:

        - use front page url as our fixed base

        - add #PageId so the browser will scroll; most robots ignore
          this part, we think

        - have the contents page figure out"you are here" from the http referer

        """
        url = self.defaultPageUrl() + '/contents'
        if scroll: url += '#' + self.pageId()
        return url
    
    security.declareProtected(Permissions.View, 'changesUrl')
    def changesUrl(self):
        return self.urlForDtmlPageOrMethod('RecentChanges','recentchanges')

    security.declareProtected(Permissions.View, 'discussionUrl')
    def discussionUrl(self):
        p = self.pageWithName('UserDiscussion') or self.pageWithName('GeneralDiscussion')
        return (p and p.pageUrl()) or ''

    security.declareProtected(Permissions.View, 'indexUrl')
    def indexUrl(self):
        return self.urlForDtmlPageOrMethod('AllPages','') #'allpages')

    security.declareProtected(Permissions.View, 'uploadsUrl')
    def uploadsUrl(self):
        return '' #self.urlForDtmlPageOrMethod('UploadsPage','uploads')

    security.declareProtected(Permissions.View, 'preferencesUrl')
    def preferencesUrl(self):
        return self.urlForDtmlPageOrMethod('UserOptions','useroptions')

    security.declareProtected(Permissions.View, 'helpUrl')
    def helpUrl(self):
        return self.urlForDtmlPageOrMethod('HelpPage','helppage')

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
            # if the time is corrupt or missing somehow, don't beat
            # around the bush; be darn sure to give it some fixed time
            # or we'll see repeats in rss feeds & planets.
            # folder's creation time would be good but that's not
            # available.
            return DateTime(ZWIKI_BIRTHDATE)

    security.declareProtected(Permissions.View, 'lastEditTime')
    def lastEditTime(self):
        """
        Return our last edit time as a DateTime, guessing if necessary
        """
        try: return DateTime(self.last_edit_time)
        except (AttributeError,DateTimeSyntaxError):
            # similar considerations to creationTime()
            return DateTime(ZWIKI_BIRTHDATE)

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

    security.declareProtected(Permissions.View, 'lastEditInterval')
    def lastEditIntervalInHours(self):
        """
        return the number of hours since last edit
        """
        return int((self.getPhysicalRoot().ZopeTime() -
                    self.lastEditTime()) * 24)

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
  
        datepattern = ("%(nb)d %(period)s")
       
        if years:
            s = datepattern % {"nb": years, "period": years > 1 and _('years') or _('year')}
        elif months:
            s = datepattern % {"nb":months, "period":months > 1 and _('months') or _('month')}
        elif weeks:
            s = datepattern % {"nb":weeks, "period":weeks > 1 and _('weeks') or _('week')}
        elif days:
            s = datepattern % {"nb":days, "period": days > 1 and _('days') or _('day') }
        elif hours:
            s = datepattern % {"nb":hours, "period":hours > 1 and _('hours') or _('hour')}
        elif minutes:
            s = datepattern % {"nb":minutes, "period":minutes > 1 and _('minutes') or _('minute')}
        else:
            s = datepattern % {"nb":seconds, "period":seconds > 1 and _('seconds') or _('second')}
            
        return s

    security.declareProtected(Permissions.View,'include')
    def include(self,page,REQUEST=None, **kw):
        """
        Convenience method for including the body of one page within another.

        Renders without the skin, passes REQUEST in case authentication is
        needed, fails silently if page does not exist.
        """
        REQUEST = REQUEST or self.REQUEST
        p = self.pageWithNameOrId(page)
        if p: return p(bare=1,REQUEST=REQUEST, **kw)
        else: return ''
        
    def isBoring(self):
        """
        Is this page one which should be quieter, eg test pages ?

        Boring pages are pages which we don't usually want to see in blog
        listings, rss feeds etc. (?) or hear mail from unless subscribed
        directly. These are TestPage, SandBox and their offspring, by
        default. You can configure different pages in a boring_pages lines
        folder property, one per line.
        """
        boring = getattr(self,'boring_pages', BORING_PAGES)
        if self.pageName() in boring:
            return 1
        ancestors = self.ancestorsAsList()
        for p in boring:
            if p in ancestors:
                return 1
        return 0

InitializeClass(PageUtils)


# generic utilities

#logging
def STDERR(*args):  sys.stderr.write(' '.join(map(str,args)) + '\n')
def BLATHER(*args): zLOG.LOG('ZWiki',zLOG.BLATHER,' '.join(map(str,args)))
def WARN(*args):    zLOG.LOG('ZWiki',zLOG.WARNING,' '.join(map(str,args)))
def DEBUG(*args):   zLOG.LOG('ZWiki',zLOG.DEBUG,' '.join(map(str,args)))

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

def isIpAddress(s):
    """
    True if s looks like an IP address.
    """
    return re.match(r'[0-9\.\s]*$',s) and 1

def isEmailAddress(s):
    """
    True if s looks like an email address.
    """
    if type(s) is StringType and '@' in s: return 1
    else: return 0

def isUsername(s):
    """
    True if s looks like a username (for Mail.py's purposes).
    """
    return not isEmailAddress(s)

# utilities for managing lists of callable actions, "hooks" as they're
# called in emacs.  Certain core zwiki methods allow themselves to be
# extended at run-time by "hooking in" additional methods/fns, usually by
# plugins.  Cf aspect-oriented programming, method annotations, ...
#
# Declare a hook list before a method like this:
#
#   # allow extra actions to be added to this method
#   global methodname_hooks
#   methodname_hooks = []
#
# and have the method call the hooks like this:
#
#   callHooks(methodname_hooks, self)
#
# then other code can add a hook like this:
#
#   from Products.ZWiki.Utils import addHook
#   from Products.ZWiki.Modulename import methodname_hooks
#   addHook(methodname_hooks, hookmethod)
#
# the hook needs to accept the type of argument callHooks gives it.
# see eg Admin.py:upgrade and plugins/tracker/__init__.py

#def declareHook(method):
#    """
#    Declare a hook list for method, to allow extra actions to be registered.
#    """
#    import exec
#    exec (method+'_hooks = []')
#    exec ('global '+method+'_hooks')

def addHook(hooks, fn):
    """
    Add a function to a list of hook actions to be called.
    """
    hooks.append(fn)

def callHooks(hooks, arg):
    """
    Call each of a list of functions with arg, returning any error code.

    Hook functions are called with one argument.  We catch and log any
    exceptions, and return the last non-null return code if any.
    """
    err = None
    for hook in hooks:
        try:
            err = hook(arg) or err
        except:
            BLATHER(
                'could not call hook, skipping (traceback follows)\n%s' % (
                formattedTraceback()))
    return err
