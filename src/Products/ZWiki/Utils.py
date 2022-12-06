######################################################################
#  miscellaneous utility methods and functions

from types import *
from string import split,join,find,lower,rfind,atoi,strip,lstrip
import os, re, sys, traceback, math
from urllib import quote, unquote

from Acquisition import aq_base
from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import absattr
from AccessControl.class_init import InitializeClass
from OFS.SimpleItem import SimpleItem
import zLOG
from DateTime import DateTime
try: #Zope4
    from DateTime.interfaces import SyntaxError as DateTimeSyntaxError
except ImportError:
    try: #Zope2.13
        DateTimeSyntaxError = DateTime.SyntaxError
    except AttributeError: # Zope2.7
        from DateTime import SyntaxError
        DateTimeSyntaxError = SyntaxError()

from App.version_txt import getZopeVersion
# getZopeVersion => (major, minor, micro, status, release)
# ZOPEVERSION: major, minor, micro
ZOPEVERSION = getZopeVersion()[:3]

from Products.ZWiki import __version__
from Defaults import PREFER_USERNAME_COOKIE, PAGE_METADATA, BORING_PAGES, \
                     PAGE_METATYPE
import Permissions
from i18n import _

# adapt to zope 2.9 transaction api
try: from transaction import get as get_transaction
except ImportError: get_transaction = get_transaction

ZWIKI_BIRTHDATE='1999/11/05'

ZWIKIDIR = os.path.dirname(__file__)
def abszwikipath(path): return os.path.join(ZWIKIDIR,path)

def container(ob):
    """Reliably get this zodb object's container, ignoring acquisition
    paths.  Work for zwiki pages without a proper acquisition wrapper too.
    """
    return getattr(getattr(ob,'aq_inner',ob),'aq_parent',None)

SUPPORT_FOLDER_IDS = []

def registerSupportFolderId(id):
    """Mixins and plugins may register any special folder ids here at
    startup, so that the product as a whole can identify them."""
    SUPPORT_FOLDER_IDS.append(id)

def isSupportFolder(folder):
    """Is this folder one of Zwiki's special support folders ?

    We sometimes need to know whether we are in a wiki's revisions/archive
    subfolder, or in the main wiki folder. Here are some alternatives
    considered:

    1. use known folder ids like 'revisions' or 'archive - this means your
       wiki will break if you happen to choose that id for the wiki folder.

    2. use ids, but more obscure ones like 'zwiki_revisions' or
       'revisions_' - old wikis will break and need (quick) upgrading;
       urls are not as nice

    3. use a custom folder type - old wikis will break and need upgrading;
       custom types in the zodb are a pain with their ingrained module
       paths

    4. use folders with a marker attribute added - old wikis will break
       and need (quick) upgrading; folders that look normal but aren't
       seems like fertile ground for gotchas (but, when would you ever
       manually create an archive/revisions folder; and copy/pasting a
       wiki should still work)

    For now we stick with 1. We could detect and warn in the failure mode,
    but we don't yet.
    """
    return folder.getId() in SUPPORT_FOLDER_IDS

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
            name = mailin_name or cookie_name or authenticated_name or ip_addr
        else:
            name = mailin_name or authenticated_name or cookie_name or ip_addr
        return self.tounicode(name)

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

    def summary(self,size=200,paragraphs=1):
        """
        Give a short plaintext summary of this page's content.

        We generate this by excerpting the first paragraph.
        Specifically, we take the page's document part, strip html tags,
        and return up to the specified number of characters or paragraphs,
        replacing the last word with an ellipsis if we had to truncate.
        """
        size, paragraphs = int(size), int(paragraphs)
        t = self.documentPart()
        t = re.sub(r'<(?=\S)[^>]+>','',t).strip() # strip html tags
        if paragraphs: t = join(split(t,'\n\n')[:paragraphs],'\n\n')
        if len(t) > size:
            t = t[:size]
            t = re.sub(r'\w*$',r'',t) + '...'
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
                    self,
                    self.summary(size=size, paragraphs=paragraphs))))

    security.declareProtected(Permissions.View, 'excerptAt')
    def excerptAt(self, expr, size=100, highlight=1, text=None): # -> html string | empty string
        # depends on: self (if no text provided)
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

        If the arguments are not unicode or convertible to unicode,
        returns the empty string.
        """
        text = text or self.text()
        try: text, expr = tounicode(text), tounicode(expr)
        except UnicodeDecodeError: return ''
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
                    '<span class="hit" style="background-color:yellow;font-weight:bold;">%s</span>' % html_quote(m.group()),
                    excerpt)
        else:
            excerpt = html_quote(text[:size])
        return excerpt

    def metadataFor(self,page):
        """
        Make a catalog-brain-like object containing page's principal metadata.

        Given a real page object, this returns a PageBrain which emulates
        a catalog brain object (search result), for use when there is no
        catalog. All PAGE_METADATA fields will be included, plus a few more
        for backwards compatibility with old skin templates.

        Warning: fields such as the parents list may be
        copies-by-reference, and should not be mutated.

        Since we're ensuring that we always have a catalog now (since 0.60),
        this thing should not be needed any more. XXX remove this method?
        """
        if getattr(page, 'meta_type', None)!=PAGE_METATYPE:
            raise TypeError(str(page)+' is not a '+PAGE_METATYPE)
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
            if not safe_hasattr(brain,attr):
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
    def htmlquote(self, text): # -> string
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

    def urlForPageOrMethod(self,pagename,methodname):
        """
        Return the url of the named wiki page if it exists, otherwise
        the url of the named method on the default page. Used for our
        "wiki page overrides built-in page template" behaviour.
        """
        p = self.pageWithName(pagename)
        return ((p and p.pageUrl())
                or self.defaultPage().pageUrl()+'/'+methodname)

    def urlForDtmlPageOrMethod(self,pagename,methodname):
        """
        Like urlForPageOrMethod, where the page must not only exist
        but have functioning dynamic content (ie, DTML is enabled).
        Early zwikis always had RecentChanges, SearchPage
        etc. in-wiki, but when DTML became disabled by default those
        pages no longer worked; this method avoids using them in that
        situation.
        """
        p = self.pageWithName(pagename)
        return ((p and p.dtmlAllowed() and p.hasDynamicContent() and p.pageUrl())
                or self.defaultPage().pageUrl()+'/'+methodname)

    # XXX keeping these page names in the skin might be easier for i18n ?
    # but way too cumbersome right now
    security.declareProtected(Permissions.View, 'homeUrl')
    def homeUrl(self):
        return self.defaultPageUrl()

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

    discussionUrl = defaultPageUrl

    security.declareProtected(Permissions.View, 'indexUrl')
    def indexUrl(self):
        return self.urlForDtmlPageOrMethod('Index','wikiindex')

    security.declareProtected(Permissions.View, 'statsUrl')
    def statsUrl(self):
        return self.urlForDtmlPageOrMethod('WikiStats','wikistats')

    security.declareProtected(Permissions.View, 'uploadsUrl')
    def uploadsUrl(self):
        return '' #self.urlForDtmlPageOrMethod('UploadsPage','uploads')

    security.declareProtected(Permissions.View, 'preferencesUrl')
    def preferencesUrl(self):
        """
        Produce the link for the "options" page, also transmitting
        the current page URL to redirect back to.
        """
        prefurl = self.urlForDtmlPageOrMethod('UserOptions','useroptions')
        return prefurl + '?redirectURL='+quote(self.pageUrl())

    security.declareProtected(Permissions.View, 'helpUrl')
    def helpUrl(self):
        return self.urlForPageOrMethod('HelpPage','helppage')

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
        """Return this page's containing folder."""
        return container(self)

    def wikiFolder(self):
        """Get the main wiki folder, which may not be our container if
        this is a saved revision or archived page."""
        f = self.folder()
        if isSupportFolder(f): return container(f)
        else: return f

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
    def asAgeString(self,time): # -> string | empty string
        # depends on: self (for current time)
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

    def talsafe(self,s):
        """
        Make a string safe for use with TAL's structure keyword across
        zope versions.

        Zope versions before 2.10 expect such data to be an ordinary
        string.  Zope 2.10 expects it to be unicode, or to at least be
        convertible to unicode using the default encoding.  We can't
        guarantee the latter, so convert to unicode preemptively assuming
        our standard encoding.  (cf issue #1330)

        This is idempotent, safe to call repeatedly.
        """
        if ZOPEVERSION < (2,10): return s
        else:                    return self.tounicode(s)

    # XXX once unicode text handling has settled down, we could try making
    # this smarter and handle different encodings, perhaps configured per
    # wiki as a folder property ? For this reason these are page methods,
    # which means you must have a page object to use them. As well as being
    # more verbose (self.toencoded vs. toencoded) this meant adding a page
    # argument to all the pagetype format methods. This is YAGNI code
    # but it's already done so let's leave it this way for a bit.
    def get_encoding(self):
        return 'utf-8'

    def toencoded(self,s,enc=None):
        """Safely convert a unicode string to an encoded ordinary string.
        The wiki's default encoding is used, unless overridden.
        """
        return toencoded(s,enc or self.get_encoding())

    def tounicode(self,s,enc=None):
        """Safely convert an encoded ordinary string to a unicode string.
        The wiki's default encoding is used, unless overridden.
        """
        return tounicode(s,enc or self.get_encoding())

InitializeClass(PageUtils)

def toencoded(s,enc='utf8'):
    """Safely convert a unicode string to an encoded ordinary string.
    UTF8 is used by default."""
    if isunicode(s): return s.encode(enc)
    else:            return s

def tounicode(s,enc='utf8'):
    """Safely convert an encoded ordinary string to a unicode string.
    UTF8 is used by default."""
    if isunicode(s): return s
    else:
        try:
            s2 = s.decode(enc)
        except UnicodeDecodeError:
            DEBUG("failed to decode %s with encoding %s" % (repr(s),enc))
            raise
        return s2


# generic utilities

#logging
def STDERR(*args):  sys.stderr.write(' '.join(map(str,args)) + '\n')
def LOG(severity,*args): zLOG.LOG('ZWiki',severity,' '.join(map(toencoded,*args)))
def TRACE(*args):   LOG(zLOG.TRACE,  args)
def DEBUG(*args):   LOG(zLOG.DEBUG,  args)
def BLATHER(*args): LOG(zLOG.BLATHER,args)
def INFO(*args):    LOG(zLOG.INFO,   args)
def WARNING(*args): LOG(zLOG.WARNING,args)
def ERROR(*args):   LOG(zLOG.ERROR,  args)


def formattedTraceback():
    type,val,tb = sys.exc_info()
    try:     return join(traceback.format_exception(type,val,tb),'')
    finally: del tb  # Clean up circular reference, avoid IssueNo0536

def safe_hasattr(obj, name, _marker=object()):
    """Make sure we don't mask exceptions like hasattr().

    We don't want exceptions other than AttributeError to be masked,
    since that too often masks other programming errors.
    Three-argument getattr() doesn't mask those, so we use that to
    implement our own hasattr() replacement.
    """
    return getattr(obj, name, _marker) is not _marker

def base_hasattr(obj, name):
    """Like safe_hasattr, but also disables acquisition."""
    return safe_hasattr(aq_base(obj), name)

def html_quote(s):
    s = re.sub(r'&','&amp;',s)
    s = re.sub(r'<','&lt;',s)
    s = re.sub(r'>','&gt;',s)
    return s

def html_unquote(s, character_entities=(
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
    elif safe_hasattr(i,'section'):
        flatList.extend(flattenDtmlParse(i.section))
    elif safe_hasattr(i,'im_self'):
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

def nonnulls(xs): return [x for x in xs if x]

def stripList(lines):
    """
    Strip leading and trailing whitespace from each of a list of
    strings, then strip out any empty strings. Useful for cleaning
    up a zope lines property. Also accepts a tuple of strings.
    """
    return nonnulls(map(strip, list(lines)))

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

# provide sorted for python 2.3
if not safe_hasattr(__builtins__,'sorted'):
    def sorted(L):
        L = L[:]
        L.sort()
        return L
else:
    sorted = sorted

# unique values of a list
def nub(l):
    u = []
    for v in l:
        if not v in u: u.append(v)
    return u

isnumeric = lambda v:isinstance(v,IntType) or isinstance(v,FloatType) or isinstance(v,LongType)
isfloat   = lambda v:isinstance(v,FloatType)
isstring  = lambda v:isinstance(v,StringType)
isunicode = lambda v:isinstance(v,UnicodeType)
