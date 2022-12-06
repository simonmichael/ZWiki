"""
The main Zwiki module. See README.txt.

(c) 1999-2004 Simon Michael <simon@joyful.com> for the zwiki community.
Wikiwikiweb formatting by Tres Seaver <tseaver@zope.com>
Parenting code and regulations by Ken Manheimer <klm@zope.com>
Initial Zope CMF integration by Chris McDonough <chrism@zope.com>
Full credits are at http://zwiki.org/ZwikiContributors .

This product is available under the GNU GPL.  All rights reserved, all
disclaimers apply, etc.
"""

from __future__ import nested_scopes
import os, sys, re, string, time, thread
from string import split,join,find,lower,rfind,atoi,strip
from urllib import quote, unquote
from types import *

#import ZODB # need this for pychecker
from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import rfc1123_date
from DateTime import DateTime
from AccessControl.class_init import InitializeClass
from OFS.DTMLDocument import DTMLDocument
from zope.interface import implements
import Permissions
from Defaults import AUTO_UPGRADE, IDS_TO_AVOID, \
     PAGE_METATYPE, LINK_TO_ALL_CATALOGED, LINK_TO_ALL_OBJECTS, \
     WIKINAME_LINKS, BRACKET_LINKS, DOUBLE_BRACKET_LINKS, \
     DOUBLE_PARENTHESIS_LINKS, ISSUE_LINKS, PAGE_METADATA, \
     CONDITIONAL_HTTP_GET, CONDITIONAL_HTTP_GET_IGNORE
from Regexps import url, bracketedexpr, singlebracketedexpr, \
     doublebracketedexpr, doubleparenthesisexpr, wikiname, wikilink, \
     interwikilink, remotewikiurl, protected_line, zwikiidcharsexpr, \
     anywikilinkexpr, markedwikilinkexpr, localwikilink, \
     spaceandlowerexpr, dtmlorsgmlexpr, wikinamewords, hashnumberexpr, \
     bracketmatch
from Utils import PageUtils, BLATHER, DateTimeSyntaxError, isunicode, \
     safe_hasattr, ZOPEVERSION
from Views import PageViews
from OutlineSupport import PageOutlineSupport
from Archive import ArchiveSupport
from Diff import PageDiffSupport # XXX to be replaced by..
from History import PageHistorySupport
from Mail import PageSubscriptionSupport, PageMailSupport, PageMailinSupport
from Catalog import PageCatalogSupport
from CMF import PageCMFSupport
from Comments import PageCommentsSupport
from Admin import PageAdminSupport
from Editing import PageEditingSupport
from i18n import DTMLFile, _
from plugins.pagetypes import PAGETYPES, PAGE_TYPES, pageTypeWithId
from plugins.pagetypes.common import MIDSECTIONMARKER
from plugins.pagetypes.stx import PageTypeStx
from plugins import PLUGINS

DEFAULT_PAGETYPE = PAGETYPES[0]

# see plugins/__init__.py
#
# PageCMFSupport is last to avoid PortalContent.id overriding
# DTMLDocument.id() as older code expects ZWikiPage.id() to be callable.
class ZWikiPage(
    PLUGINS[0],
    PLUGINS[1],
    PLUGINS[2],
    PLUGINS[3],
    PLUGINS[4],
    PLUGINS[5],
    PLUGINS[6],
    PLUGINS[7],
    PLUGINS[8],
    PLUGINS[9],
    PLUGINS[10],
    PLUGINS[11],
    PLUGINS[12],
    PLUGINS[13],
    PLUGINS[14],
    PLUGINS[15],
    ArchiveSupport,
    PageEditingSupport,
    PageOutlineSupport,
    PageDiffSupport,
    PageHistorySupport,
    PageMailSupport,
    PageMailinSupport,
    PageSubscriptionSupport,
    PageCatalogSupport,
    PageCommentsSupport,
    PageAdminSupport,
    PageUtils,
    PageViews,
    DTMLDocument,
    PageCMFSupport,
    ):
    """
    A ZWikiPage is essentially a DTML Document which knows how to render
    itself in various wiki styles, and can function inside or outside a
    CMF site. A lot of extra methods are provided to support
    wiki-building, email, issue tracking, etc.  Mixins are used to
    organize functionality into modules.
    """
    if ZOPEVERSION < (2,12):
        from webdav.WriteLockInterface import WriteLockInterface
        __implements__ = (WriteLockInterface, PageCMFSupport.__implements__)

    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
    security.declareProtected(Permissions.Edit, 'revert')
    security.declareProtected(Permissions.Edit, 'manage_upload')
    security.declareProtected(Permissions.FTP, 'manage_FTPstat') # needed
    security.declareProtected(Permissions.FTP, 'manage_FTPlist') # ?

    def checkPermission(self, permission, object):
        return getSecurityManager().checkPermission(permission,object)

    # perms need at least one declaration (in this file ?) to be recognized
    # this is dumb indeed.. need tests to figure out the rules of this game
    security.declareProtected(Permissions.ChangeType, 'dummy')
    def dummy(self): pass
    security.declareProtected(Permissions.Reparent, 'dummy2')
    def dummy2(self): pass

    # properties visible in the ZMI
    _properties=(
        # XXX title is read only for now to avoid de-syncing title & id
        # but they can still rename in ZMI.. we should override
        # manage_changeProperties and manage_renameObject perhaps
        # reverted - too many breakages
        {'id':'title', 'type': 'string', 'mode':'w'},
        # page_type is now an object.. can we show pageTypeId() ?
        #{'id':'page_type', 'type': 'selection', 'mode': 'w',
        # 'select_variable': 'ALL_PAGE_TYPES'},
        {'id':'creator', 'type': 'string', 'mode': 'r'},
        {'id':'creator_ip', 'type': 'string', 'mode': 'r'},
        {'id':'creation_time', 'type': 'string', 'mode': 'r'},
        {'id':'last_editor', 'type': 'string', 'mode': 'r'},
        {'id':'last_editor_ip', 'type': 'string', 'mode': 'r'},
        {'id':'last_edit_time', 'type': 'string', 'mode': 'r'},
        {'id':'last_log', 'type': 'string', 'mode': 'r'},
        {'id':'revision_number', 'type': 'int', 'mode': 'r'},
        ) \
        + PageOutlineSupport._properties \
        + PageSubscriptionSupport._properties \
        + PageCatalogSupport._properties

    meta_type = PAGE_METATYPE
    icon      = "misc_/ZWiki/ZWikiPage_icon"
    creator = ''
    creator_ip = ''
    creation_time = ''
    last_editor = ''
    last_editor_ip = ''
    last_edit_time = ''
    last_log = ''
    revision_number = 1
    PAGE_TYPES = PAGE_TYPES # used by skin templates
    # page_type used to be a string used to select a render method.
    # As of 0.25 it is an object which encapsulates the page's formatting
    # behaviour. It will return the old id string when called, which
    # should keep existing catalogs working.
    page_type = DEFAULT_PAGETYPE()
    # pre-rendered text cache
    _prerendered = ''

    def __unicode__(self):
        return self.tounicode(self.read())

    def __str__(self):
        return self.toencoded(self.read())

    def setPageType(self,id=None):
        self.page_type = id

    security.declareProtected('Manage properties', 'setType')
    def setType(self,type=DEFAULT_PAGETYPE):
        """Quietly (without leaving history or sending mail) change
        this page's page type and re-render it. A helper for
        admin cleanup."""
        self.setPageType(type)
        self.clearCache()
        self.index_object()
        self.REQUEST.RESPONSE.redirect(self.pageUrl())

    security.declarePublic('pageType')
    def pageType(self):
        """Return this page's page type as a page type object."""
        if AUTO_UPGRADE: self.upgradePageType()
        return pageTypeWithId(self.page_type)()

    security.declarePublic('pageTypeId')
    def pageTypeId(self): # useful for troubleshooting
        """Return the short id for this page's page type."""
        return self.pageType().getId()

    security.declarePublic('lookupPageType')
    def lookupPageType(self,id=None):
        """Return the page type object with this id (or the default)"""
        match = filter(lambda x:x._id==id,PAGETYPES)
        return (match and match[0]) or DEFAULT_PAGETYPE

    def setPreRendered(self,t): self._prerendered = t

    def preRendered(self):
        # cope with non-existing or None attribute on old instances - needed ?
        try:
            return unicode(getattr(self,'_prerendered','') or '')
        except UnicodeError:
            return ''

    ######################################################################
    # initialization

    def __init__(self, source_string='', mapping=None, __name__=''):
        """
        Initialise this instance, including it's CMF data if applicable.

        Ugly, but putting PageCMFSupport before DTMLDocument in the
        inheritance order creates problems.
        """
        if self.supportsCMF():
            PageCMFSupport.__init__(self,
                                  source_string=source_string,
                                  mapping=mapping,
                                  __name__=__name__,
                                  )
        else:
            DTMLDocument.__init__(self,
                                  source_string=source_string,
                                  mapping=mapping,
                                  __name__=__name__,
                                  )

    ######################################################################
    # generic rendering code (see also pagetypes/*)

    security.declareProtected(Permissions.View, '__call__')
    def __call__(self, client=None, REQUEST={}, RESPONSE=None, **kw):
        """
        Render this zwiki page, or, return a cache-friendly 304 response
        if it seems appropriate. Also upgrade it on the fly if needed.
        """
        if AUTO_UPGRADE: self.upgrade(REQUEST)
        if self.handle_modified_headers(REQUEST=REQUEST): return ''
        else: return self.render(client,REQUEST,RESPONSE,**kw)

    def render(self, client=None, REQUEST={}, RESPONSE=None, **kw):
        """
        Render this page according to it's page_type.

        Also tries to ensure the HTTP content-type (and charset) have an
        appropriate value. These may be set by the page type, or
        overridden by a zwiki_content_type property (LatexWiki support).
        NB this can also get set in I18n.py.
        """
        if not self.preRendered(): self.preRender()
        r = self.pageType().render(self, REQUEST, RESPONSE, **kw)
        if RESPONSE:
            if safe_hasattr(self,'zwiki_content_type'):
                RESPONSE.setHeader('content-type',getattr(self,'zwiki_content_type'))
            elif not RESPONSE.getHeader('content-type'):
                RESPONSE.setHeader('content-type','text/html')
        return r

    def preRender(self,clear_cache=0):
        """
        Make sure any applicable pre-rendering for this page has been done.

        If clear_cache is true, blow away any cached data.
        XXX I think this happens anyway.
        """
        if clear_cache: self.clearCache()
        self.setPreRendered(self.pageType().preRender(self))

    security.declarePublic('renderText')
    def renderText(self, text, type, **kw):
        """
        Render some source text according to the specified page type.
        """
        return self.lookupPageType(type)().renderText(self,text,**kw)

    security.declareProtected(Permissions.View, 'clearCache')
    def clearCache(self,REQUEST=None):
        """
        forcibly clear out any cached render data for this page
        """
        self.setPreRendered('')
        if safe_hasattr(self,'_v_cooked'):
            delattr(self,'_v_cooked')
            delattr(self,'_v_blocks')
        if REQUEST: REQUEST.RESPONSE.redirect(self.pageUrl())

    clear = clearCache

    def cookDtmlIfNeeded(self):
        if self.dtmlAllowed() and self.hasDynamicContent(): self.cook()

    security.declareProtected(Permissions.View, 'cook')
    def cook(self, cooklock=thread.allocate_lock()):
        """
        Pre-parse this page's text (the pre-rendered, if available) for DTML.
        """
        t = self.preRendered() or self.read()
        # dtml can break with a unicode string here (eg
        # test_dtml_in_rst); we'll encode it and decode again in
        # evaluatePreRenderedAsDtml
        t = self.toencoded(t)
        cooklock.acquire()
        try:
            self._v_blocks=self.parse(t)
            self._v_cooked=None
        finally:
            cooklock.release()

    def evaluatePreRenderedAsDtml(self,client=None, REQUEST={},
                                  RESPONSE=None, **kw):
        # optimization: to save memory, avoid unnecessarily calling DTML
        # and generating _v_blocks data
        if not self.hasDynamicContent(): return self.preRendered()
        t = DTMLDocument.__call__(
            self.__of__(self.folder()), # ensure dtml in pages can acquire
            client,
            REQUEST,
            RESPONSE,
            **kw)
        # cook encoded it for safe passage through the DTML monster
        t = self.tounicode(t)
        return t

    def renderMidsectionIn(self, text, **kw):
        """
        Insert some final things between the rendered document and discussion.

        A page's "midsection" is after the pristine gem-like main document,
        right before the mudslinging. This is where we want to put the
        automatic children list (subtopics), next/prev links, etc.

        XXX This is not good enough. The midsection marker can get mixed
        up with other rendering in the various page types.

        """
        # page may not have been prerendered with midsection marker yet -
        # we'll also insert at a messages separator, if we see one,
        # otherwise leave it be
        if string.find(text,MIDSECTIONMARKER) != -1:
            try: doc, discussion = re.split(MIDSECTIONMARKER,text)
            except ValueError:
                #our marker got clobbered, or there's more than one - bail out
                return text

        elif string.find(text,r'<a name="messages">') != -1:
            doc, discussion = re.split(r'<a name="messages">',text)
            discussion = '<a name="messages">' + discussion
        else:
            return text
        return doc + self.renderMidsection(**kw) + discussion

    def renderMidsection(self,**kw):
        """
        Render whatever should be in this page's midsection.

        This is the subtopics, in the preferred style, if enabled, or
        nothing.  As a convenience, if it seems subtopics are already
        displayed via custom DTML code, we won't display them again.
        """
        if self.subtopicsEnabled(**kw) and not self.displaysSubtopicsWithDtml():
            return self.subtopics()
        else:
            return ''

    def displaysSubtopicsWithDtml(self):
        """
        True if this page appears to display subtopics via custom DTML.
        """
        return (self.hasDynamicContent() and
                self.dtmlAllowed() and
                (re.search(r'(?i)(<dtml-var[^>]+subtopics|&dtml-subtopics)',
                           self.read()) is not None))

    security.declareProtected(Permissions.View, 'supportsStx')
    def supportsStx(self):
        """supportsStx"""
        return self.pageType().supportsStx()

    security.declareProtected(Permissions.View, 'supportsRst')
    def supportsRst(self):
        """supportsRst"""
        return self.pageType().supportsRst()

    security.declareProtected(Permissions.View, 'supportsWikiLinks')
    def supportsWikiLinks(self):
        """supportsWikiLinks"""
        return self.pageType().supportsWikiLinks()

    security.declareProtected(Permissions.View, 'supportsHtml')
    def supportsHtml(self):
        """Does this page render ordinary HTML tags ?"""
        return self.pageType().supportsHtml()

    security.declareProtected(Permissions.View, 'supportsDtml')
    def supportsDtml(self):
        """Does this page support embedded DTML ?"""
        return self.pageType().supportsDtml()

    security.declareProtected(Permissions.View, 'hasDynamicContent')
    def hasDynamicContent(self):
        """hasDynamicContent"""
        return (self.supportsDtml() and
                re.search(r'(?i)(<dtml|&dtml)',self.read()) is not None)

    security.declareProtected(Permissions.View, 'dtmlAllowed')
    def dtmlAllowed(self):
        """Is embedded DTML permitted on this page ?"""
        return (
            getattr(self,'allow_dtml',0) and
            not safe_hasattr(self,'no_dtml')
            )

    def handle_modified_headers(self, last_mod=None, REQUEST=None):
        """
        Check if the headers indicate we have changed content.

        Return True if nothing changed, False otherwise. Set Headers as needed.
        Methods using this should call this before returning any content,
        then if a 304 is called for this method returns True and
        the calling method should give no content to the browser.
        """
        RESPONSE = getattr(REQUEST,'RESPONSE',None)
        if not RESPONSE:return False
        RESPONSE.setHeader('Cache-Control',
            'max-age=86400, s-maxage=86400, public, must-revalidate, proxy-revalidate')
        # do we handle things at all?
        if not getattr(self, 'conditional_http_get', CONDITIONAL_HTTP_GET):
            return False
        # admins can specify a list of property names that make us ignore
        # "Conditional HTTP Get" processing if they are set
        # especially useful for ignoring pages with allow_dtml
        ignore = getattr(
            self, 'conditional_http_get_ignore', CONDITIONAL_HTTP_GET_IGNORE)

        for ignore_property in ignore:
            if getattr(self, ignore_property, False): return False
        if last_mod == None:
            try:
                # modification time reflects also changes
                # to voting, not like last_edit_time
                last_mod = DateTime(self.last_modified(self))
            except DateTimeSyntaxError:
                # if anything goes wrong with the stored date, we just
                # ignore all 304 handling and go on as if nothing happened
                BLATHER("invalid modification time in page %s" \
                            % (self.id()))
                return False
        try: # we could have been fed an illegal date string
            last_mod = long(DateTime(last_mod).timeTime())
        except DateTimeSyntaxError:
            BLATHER("invalid date input on page %s" % (self.id()))
            return False
        header=REQUEST.get_header('If-Modified-Since', None)
        if header is not None:
            header=header.split( ';')[0]
            # Some proxies seem to send invalid date strings for this
            # header. If the date string is not valid, we ignore it
            # rather than raise an error to be generally consistent
            # with common servers such as Apache (which can usually
            # understand the screwy date string as a lucky side effect
            # of the way they parse it).
            # This happens to be what RFC2616 tells us to do in the face of an
            # invalid date.
            try:   mod_since=long(DateTime(header).timeTime())
            except DateTimeSyntaxError: mod_since=None
            if mod_since is not None:
                if last_mod > 0 and last_mod <= mod_since:
                    RESPONSE.setHeader('Last-Modified',rfc1123_date(last_mod))
                    RESPONSE.setStatus(304)
                    return True
        RESPONSE.setHeader('Last-Modified', rfc1123_date(last_mod))
        return False

    # link rendering and handling

    def wikinameLinksAllowed(self):
        """Are wikinames linked in this wiki ?"""
        return getattr(self,'use_wikiname_links',WIKINAME_LINKS)

    def issueLinksAllowed(self):
        """Are issue numbers (#NNNN) linked in this wiki ?"""
        return getattr(self,'use_issue_links',ISSUE_LINKS)

    def bracketLinksAllowed(self):
        """Are bracketed freeform names linked in this wiki ?"""
        return getattr(self,'use_bracket_links',BRACKET_LINKS)

    def doubleBracketLinksAllowed(self):
        """Are wikipedia-style double bracketed names linked in this wiki ?"""
        return getattr(self,'use_double_bracket_links',DOUBLE_BRACKET_LINKS)

    def doubleParenthesisLinksAllowed(self):
        """Are wicked-style double parenthesis names linked in this wiki ?"""
        return getattr(
            self,'use_double_parenthesis_links',DOUBLE_PARENTHESIS_LINKS)

    def isWikiName(self,name):
        """Is name a WikiName ?"""
        return re.match('^%s$' % wikiname,name) is not None

    def isValidWikiLinkSyntax(self,link):
        """Does link look a valid wiki link syntax for this wiki ?
        """
        return ((
            (self.wikinameLinksAllowed() and
                re.match(wikiname,link))
            or (self.issueLinksAllowed() and
                re.match(hashnumberexpr,link))
            or (self.bracketLinksAllowed() and
                re.match(singlebracketedexpr,link))
            or (self.doubleBracketLinksAllowed() and
                re.match(doublebracketedexpr,link))
            or (self.doubleParenthesisLinksAllowed() and
                re.match(doubleparenthesisexpr,link))) and 1)

    def firstBracketStyle(self): # -> tuple of strings
        """
        Find the first allowed freeform link syntax.
        """
        if self.bracketLinksAllowed(): return ('[', ']')
        if self.doubleBracketLinksAllowed(): return ('[[', ']]')
        if doubleParenthesisLinksAllowed(): return ('((', '))')
        else:
            # XXX: raise? or return something that won't work?
            return ('[', ']')

    def markLinksIn(self,text,urls=1):
        """
        Find and mark links in text, for fast replacement later.

        Successor to _preLink. Instead of generating a list of text
        extents and link names, this simply marks the links in place to
        make them easy to find again.  Tries to be smart about finding
        links only where you want it to.

        As well as all kinds of Zwiki wiki-links, marks bare urls, unless
        urls is false (useful for restructured text).
        """
        markedtext = ''
        state = {'lastend':0,'inpre':0,'incode':0,'intag':0,'inanchor':0}
        lastpos = 0
        while 1:
            m = anywikilinkexpr.search(text,lastpos)
            if m:
                # found some sort of link pattern - check if we should link it
                link = m.group()
                linkstart,linkend = m.span()
                if (link[0]=='!'
                    or not (self.isValidWikiLinkSyntax(link)
                            or (urls and re.match(url,link))
                            )
                    or within_literal(linkstart,linkend-1,state,text) # XXX these
                    or withinSgmlOrDtml((linkstart,linkend),text)):   # overlap ?
                    # no - ignore it (and strip the !)
                    if link[0] == '!':
                        link=link[1:]
                    markedtext += text[lastpos:linkstart] + link
                else:
                    # yes - mark it for later
                    markedtext += '%s<zwiki>%s</zwiki>' \
                                  % (text[lastpos:linkstart],link)
                lastpos = linkend
            else:
                # no more links - save the final text extent & quit
                markedtext += text[lastpos:]
                break
        return markedtext

    def renderMarkedLinksIn(self,text):
        """
        Render the links in text previously marked by markLinksIn.
        """
        return re.sub(markedwikilinkexpr,self.renderLink,text)
        #XXX optimisation - could call renderLink for unique links only

    def renderLinksIn(self,text):
        """
        Find and render all links in text in one step.

        An alternative to the more usual markLinksIn + renderMarkedLinksIn.
        """
        t = self.applyWikiLinkLineEscapesIn(text)
        # ken's clever thunk_substituter helps keep track of state
        return re.sub(anywikilinkexpr, thunk_substituter(self.renderLink, t), t)

    wikilink = renderLinksIn # convenience alias

    security.declareProtected(Permissions.View, 'applyWikiLinkLineEscapesIn')
    def applyWikiLinkLineEscapesIn(self, text):
        """
        Escape all wikilinks in lines in text which begin with !.
        """
        return re.sub(
            protected_line,
            lambda m:re.sub(wikilink, r'!\1', m.group(1)),
            text)

    def renderLink(self,link,state=None,text='',link_title=None,access_key=None):
        """
        Render various kinds of hyperlink, based on page and wiki state.

        Can be called three ways:
        - directly (link should be a string)
        - from re.sub (link will be a match object, state will be None)
        - from re.sub via thunk substituter (state will be a dictionary) (old)
        """
        # preliminaries
        if not link: return ''
        if type(link) == StringType:
            text = self.preRendered()
        elif state == None:
            link = link.group()
            text = self.preRendered()
        else:
            match = link
            link = match.group()
            # we are being called from re.sub, using thunk_substituter to
            # keep state - do the within_literal and within sgml checks that
            # would normally be done in markLinksIn
            if (within_literal(match.start(),match.end()-1,state,text) or
                withinSgmlOrDtml(match.span(),text)):
                return link
        link = linkorig = re.sub(markedwikilinkexpr, r'\1', link)
        label = None

        # here we go
        # is this link escaped ?
        if link[0] == '!':
            return link[1:]

        # ignore certain WikiNames from a property ('Lines' type property)
        ignore_wikinames = getattr(self, 'ignore_wikinames', [])
        if link in ignore_wikinames:
            return link

        # is it an interwiki link ?
        if re.match(interwikilink,link):
            return self.renderInterwikiLink(link)

        # is it a STX footnote ? check for matching named anchor in the page text
        if re.match(singlebracketedexpr,link):
            linknobrackets = re.sub(singlebracketedexpr, r'\1', link)
            if re.search(
                r'(?s)<a name="ref%s"' % (re.escape(linknobrackets)),text):
                return '<a href="%s#ref%s" title="footnote %s">[%s]</a>' % (
                    self.pageUrl(),linknobrackets,
                    linknobrackets,linknobrackets)

        # is it a bare URL ?
        if re.match(url,link):
            label = re.sub(r'^mailto:','',link)
            return '<a href="%s">%s</a>' % (link, label)

        # is it a hash number issue link (#123) ?
        if re.match(hashnumberexpr,link):
            # yes - convert to the id of the issue page with that number
            # and continue; if we can't, don't bother linking
            p = self.issuePageWithNumber(self.issueNumberFrom(link))
            if p:
                try: link = p.getId() # XXX poor caching
                except AttributeError: link = p.id   # all-brains
                return self.renderLinkToPage(link,
                                             linkorig=linkorig,
                                             link_title=link_title,
                                             access_key=access_key)
            else:
                return linkorig

        # is it a wiki link, of a kind that's allowed in this wiki ?
        # (bare, bracketed, double bracketed, double parenthesis)
        if not self.isValidWikiLinkSyntax(link):
            # no - we have exhausted our linking arsenal, give up
            return linkorig

        # is it a freeform (bracketed) wiki link ?
        if not self.isWikiName(link):
            # yes - use fuzzy matching to match an existing page if possible.
            # strip brackets/parentheses
            link = stripDelimitersFrom(linkorig)
            # XXX experimental MW-style link labels
            def linkTargetAndLabel(link):
                """Return target and label from link text possibly containing |."""
                l = link.split("|")
                if len(l) < 2: l = l + ['']
                if len(l) > 2: l = [l[0], '|'.join(l[1:])]
                return l[0], l[1]
            link, label = linkTargetAndLabel(link)
            # end
            p = self.pageWithFuzzyName(link)
            if p:
                # found the page, use its id for linking
                try: link = p.getId() # XXX poor caching
                except AttributeError: link = p.id   # all-brains
            else:
                # no such page, maybe this is an external link ?
                if re.match(url,link):
                    label = re.sub(r'^mailto:','',label)
                    return '<a href="%s">%s</a>' % (link, label)
                # no - treat it as an uncreated page

        return self.renderLinkToPage(link,
                                     linkorig=linkorig,
                                     link_title=link_title,
                                     access_key=access_key,
                                     label=label)

    # XXX helper for above
    def renderLinkToPage(self,page,linkorig=None,link_title=None,
                         access_key=None,name=None,label=None):

        """
        Render a wiki link to page, which may or may not exist.

        page is renderLink's best guess at the id or name of the page
        intended.
        """
        # does page exist in this wiki ?
        p = self.pageWithNameOrId(page)
        if p:
            # yes - link to it
            # make sure we have the page's id
            if not self.pageWithId(page): # XXX this check helps avoid zodb loads ?
                try: page = p.getId() # XXX poor caching
                except AttributeError: page = p.id   # all-brains
            title     = (link_title and ' title="%s"' % link_title) or '' #' title="%s"' % self.pageWithId(page).linkTitle()
            name      = (name and ' name="%s"' % name) or ''
            accesskey = (access_key and ' accesskey="%s"' % access_key) or ''
            # XXX tracker plugin dependency
            if p.isIssue():
                try:
                    style=' style="background-color:%s;"' % p.issueColour() # poor caching
                except AttributeError:
                    style=' style="background-color:%s;"' % p.issueColour # all-brains
            else:
                style = ''
            link      = stripDelimitersFrom(linkorig or page)
            label     = label and label or self.formatWikiname(link)
            return '<a href="%s/%s"%s%s%s%s>%s</a>' % (
                self.wikiUrl(),
                quote(page),
                title,
                name,
                accesskey,
                style,
                label)
        else:
            # no - provide a creation link
            return (
                '%s<a class="new visualNoPrint" href="%s/%s/createform?page=%s" title="%s">?</a>' % (
                self.formatWikiname(linkorig or page),
                self.wikiUrl(),
                quote(self.id()),
                quote(self.toencoded(page)),
                _("create this page")))

    def renderInterwikiLink(self, link):
        """
        Render an occurence of interwikilink. link is a string.
        """
        if link[0] == '!': return link[1:]
        m = re.match(interwikilink,link)
        local, remote  = m.group('local'), m.group('remote')
        # check local is an allowed link syntax for this wiki
        if not self.isValidWikiLinkSyntax(local): return link
        local = re.sub(bracketedexpr, r'\1', local) #XXX should support ((..))
        # look for a RemoteWikiURL definition
        localpage = self.pageWithName(local)
        if localpage:
            m = re.search(remotewikiurl, localpage.text())
            if m:
                return '<a href="%s%s">%s:%s</a>' \
                       % (m.group('remoteurl'),remote,local,remote)
                       #XXX old html_unquote needed ? I don't think so
        # otherwise return unchanged
        return link

    def _replaceLinksInSourceText(self,oldlink,newlink,text): # -> string; depends on: link styles
        """
        Replace occurrences of oldlink with newlink in a string.

        Depends on: allowed link styles (brackets etc.) on this wiki
                    or the current wiki page

        Freeform links given should not be enclosed in brackets.

        We're trying to keep each link in the style it was before
        (e.g. bracket, double parenthesis, WikiLink...)
        Only if the new page's canonical id isn't a valid WikiLink
        and the old link was a WikiLink will we make the new link
        a freeform link (choosing the simplest link style we can find).

        We'll also replace bare wiki links to a freeform page's id,
        but not fuzzy links.
        This tries not to do too much damage.
        It's slow, since it re-renders every page it changes.
        """
        markedtext = ''
        state = {'lastend':0,'inpre':0,'incode':0,'intag':0,'inanchor':0}
        lastpos = 0
        oldlink_canonical = self.canonicalIdFrom(oldlink)
        newlink_is_wikiname = self.isWikiName(newlink)
        newlink_canonical = self.canonicalIdFrom(newlink)
        newlink_canonical_is_wikiname = self.isWikiName(newlink_canonical)
        l, r = self.firstBracketStyle()
        while 1:
            m = anywikilinkexpr.search(text,lastpos)
            if m:
                # found some sort of link pattern - check if we should link it
                link = m.group()
                linkstart,linkend = m.span()
                if (not((oldlink in link) or (oldlink_canonical in link)) # not our link
                or link[0]=='!'
                or not self.isValidWikiLinkSyntax(link)
                or within_literal(linkstart,linkend-1,state,text) # XXX these
                or withinSgmlOrDtml((linkstart,linkend),text)):   # overlap ?
                    markedtext += text[lastpos:linkstart] + link
                else: # yes - change the link
                    if self.isWikiName(link):
                        if newlink_is_wikiname:
                            replacelink = newlink
                        elif newlink_canonical_is_wikiname:
                            replacelink = newlink_canonical
                        else:
                            replacelink = r'%s%s%s' % (l, newlink, r)
                    else:
                        replacelink = bracketmatch.sub(r'\1%s\3' % newlink, link)
                    markedtext += text[lastpos:linkstart] + replacelink
                lastpos = linkend
            else:
                # no more links - save the final text extent & quit
                markedtext += text[lastpos:]
                break
        return markedtext

    security.declareProtected(Permissions.View, 'formatWikiname')
    def formatWikiname(self,wikiname):
        """
        Convert a wikiname to this wiki's standard display format.

        Ie, leave it be or add ungodly spaces depending on the
        'space_wikinames' property.
        """
        if self.spacedWikinamesEnabled():
            return self.spacedNameFrom(wikiname)
        else:
            return wikiname

    security.declareProtected(Permissions.View, 'spacedNameFrom')
    def spacedNameFrom(self,pagename):
        """
        Return pagename with spaces inserted if it's a WikiName, or unchanged.

        Uses the wikiname regexp to follow localised capitalisation.
        """
        if re.match('^%s$' % wikiname, pagename):
            words = [x[0] for x in re.findall(wikinamewords,pagename)]
            return ' '.join(words)
        else:
            return pagename

    security.declareProtected(Permissions.View, 'spacedWikinamesEnabled')
    def spacedWikinamesEnabled(self):
        """Should all wikinames be displayed with spaces in this wiki ?"""
        return getattr(self.folder(),'space_wikinames',0) and 1

    security.declareProtected(Permissions.View, 'links')
    def links(self):
        """
        List the unique links occurring on this page - useful for cataloging.

        Includes urls & interwiki links but not structured text links.
        Extracts the marked links from prerendered data.
        """
        # don't generate this if missing - too expensive when cataloging ?
        #if not self.preRendered(): self.preRender()
        links = []
        for l in re.findall(markedwikilinkexpr,self.preRendered()):
            if not l in links: links.append(l)
        return links

    security.declareProtected(Permissions.View, 'canonicalLinks')
    def canonicalLinks(self):
        """
        List the canonical id form of the local wiki links in this page.

        Useful for calculating backlinks. Extracts this information
        from prerendered data, does not generate this if missing.
        """
        clinks = []
        localwikilinkexpr = re.compile(localwikilink)
        for link in self.links():
            if localwikilinkexpr.match(link):
                if link[0] == r'[' and link[-1] == r']': link = link[1:-1]
                if link[0] == r'[' and link[-1] == r']': link = link[1:-1]
                clink = self.canonicalIdFrom(link)
                clinks.append(clink)
        return clinks

    security.declareProtected(Permissions.View, 'linkTitle')
    def linkTitle(self,prettyprint=0):
        """
        return a suitable value for the title attribute of links to this page

        with prettyprint=1, format it for use in the standard header.
        """
        return self.linkTitleFrom(self.last_edit_time,
                                  self.lastEditor(),
                                  prettyprint=prettyprint)

    # please clean me up
    security.declareProtected(Permissions.View, 'linkTitleFrom')
    def linkTitleFrom(self,last_edit_time=None,last_editor=None,prettyprint=0):
        """
        make a link title string from these last_edit_time and editor strings

        with prettyprint=1, format it for use in the standard header.
        """
        try:
            interval = self.asAgeString(last_edit_time)
        except DateTimeSyntaxError:
            # we got fed with a non-valid date
            interval = self.asAgeString(None)
        if not prettyprint:
            s = _("last edited %(interval)s ago") % {"interval":interval}
        else:
            lastlog = self.lastlog()
            if lastlog and len(lastlog)>0:
                lastlog = ' ('+lastlog+')'

            # build the link around the interval
            linked_interval = (
                ' <a href="%s/history" title="%s%s" >%s</a>' % (
                self.pageUrl(),
                _('show last edit'),
                lastlog,
                interval))

            # use the link in a clear i18n way
            s =  _('last edited %(interval)s ago')  % {"interval": linked_interval}

        if (last_editor and
            # anonymous? try to find out by somehow matching an ip address:
            not re.match(r'^(?:\d{1,3}\.){3}\d{1,3}$',last_editor)):
            # escape some things that might cause trouble in an attribute
            editor = re.sub(r'"',r'',last_editor)

            #XXX cleanup
            if not prettyprint:
                s = s + " " + _("by %(editor)s")% {"editor":editor}
            else:
                s = s + " " + _("by %(editor)s") % {"editor":"<b>%s</b>" % editor}
        return s

    def linkToAllCataloged(self):
        return getattr(self,'link_to_all_cataloged',
                       LINK_TO_ALL_CATALOGED) and 1

    def linkToAllObjects(self):
        return getattr(self,'link_to_all_objects',
                       LINK_TO_ALL_OBJECTS) and 1

    ######################################################################
    # page naming and lookup

    security.declareProtected(Permissions.View, 'pageName')
    def pageName(self):
        """
        Return the name of this wiki page, as a unicode string.

        This is normally in the title attribute, but use title_or_id to
        handle eg pages created via the ZMI.
        """
        return self.tounicode(self.title_or_id())

    def pageId(self):
        return self.id()

    security.declareProtected(Permissions.View, 'spacedPageName')
    def spacedPageName(self):
        """
        Return this page's name, with spaces inserted if it's a WikiName.

        We use this for eg the html title tag to improve search engine relevance.
        """
        return self.spacedNameFrom(self.pageName())

    security.declareProtected(Permissions.View, 'formattedPageName')
    def formattedPageName(self):
        """
        Return this page's name in the standard display format (spaced or not).
        """
        return self.formatWikiname(self.pageName())

    security.declarePublic('Title')
    def Title(self):
        """
        Title
        """
        return self.pageName()

    security.declareProtected(Permissions.View, 'canonicalIdFrom')
    def canonicalIdFrom(self,name):
        """
        Convert a free-form page name to a canonical url- and zope-safe id.

        Constraints for zwiki page ids:
        - it must be a legal zope object id
        - it should be legal in urls
        - it should be unique for a given name (ignoring whitespace)
        - we'd like it to be as similar to the name and as simple to read
          and work with as possible
        - we'd like to encourage serendipitous linking between free-form
          and wikiname links & pages
        - it must avoid certain zope-significant names, to avoid breakage

        So, we
        - discard non-word-separating punctuation (')
        - convert remaining punctuation to spaces
        - capitalize and join whitespace-separated words into a wikiname
        - convert any non-zope-and-url-safe characters and _ to _hexvalue
        - if this results in an id that begins with _ (illegal), prepend X
        - or if it's one of the delicate IDS_TO_AVOID (eg REQUEST), append X
          Note these last break the uniqueness property. Better ideas welcome.

        performance-sensitive
        """
        if name == None: return None # XXX review later
        # remove punctuation, preserving word boundaries.
        # ' is not considered a word boundary.
        name = re.sub(r"'",r"",name)
        name = re.sub(r'[%s]+'%re.escape(string.punctuation),r' ',name)

        # capitalize whitespace-separated words (preserving existing
        # capitals) then strip whitespace
        id = ' '+name
        id = spaceandlowerexpr.sub(lambda m:string.upper(m.group(1)),id)
        id = string.join(string.split(id),'')

        # quote any remaining unsafe characters (international chars)
        safeid = ''
        for c in id:
            if zwikiidcharsexpr.match(c):
                safeid = safeid + c
            else:
                safeid = safeid + '_%02x' % ord(c)

        # zope ids may not begin with _
        if len(safeid) > 0 and safeid[0] == '_': safeid = 'X'+safeid

        # some ids collide with common zope objects and would break things
        if safeid in IDS_TO_AVOID: safeid = safeid+'X'

        # unicode can make it through all the above.. convert to normal string
        if isunicode(safeid): safeid = safeid.encode('ascii')

        return safeid

    security.declareProtected(Permissions.View, 'canonicalId')
    def canonicalId(self):
        """
        Give the canonical id of this page.
        """
        return self.canonicalIdFrom(self.pageName())

    # XXX poor caching when attributes are accessed
    security.declareProtected(Permissions.View, 'pageObjects')
    def pageObjects(self):
        """
        Return a list of all pages in this wiki.
        """
        return self.folder().objectValues(spec=self.meta_type)

    def wikiPath(self):
        """
        This wiki's folder path, for filtering our pages from catalog results
        """
        return self.getPath()[:self.getPath().rfind('/')]

    def hasAllCatalogFields(self):
        """Does our catalog have all the fields needed for fast queries ?"""
        return self.hasCatalogIndexesMetadata(
            (['meta_type','path'],PAGE_METADATA))

    security.declareProtected(Permissions.View, 'pages')
    def pages(self, **kw):
        """
        Look up metadata (brains) for some or all pages in this wiki.

        This is a wrapper for searching the wiki's catalog. It filters
        out results for other folders, to allow us to share a catalog
        (eg within Plone).

        Up to 0.60 it used to fall back to a (less cache-friendly)
        zodb search when there was no catalog, and this turns out to
        be bad when viewing old revisions, which don't have a catalog,
        so we no longer do that.
        """
        if not self.hasAllCatalogFields(): return []
        wikipath = self.wikiPath()
        def inthiswiki(b):
            p = b.getPath()
            return p[:p.rfind('/')] == wikipath
        return [b for b in
                self.searchCatalog(meta_type=self.meta_type,path=wikipath,**kw)
                if inthiswiki(b)]

    security.declareProtected(Permissions.View, 'pageCount')
    def pageCount(self):
        """
        Return the number of pages in this wiki.
        """
        return len(self.pages())

    security.declareProtected(Permissions.View, 'pageIds')
    def pageIds(self):
        """
        Return a list of all page ids in this wiki.

        If there's junk in the catalog, pages could return a page with id
        None; we guard against that.
        """
        # note btreefolders don't always give a list
        return list(self.folder().objectIds(spec=self.meta_type))

    security.declareProtected(Permissions.View, 'pageNames')
    def pageNames(self):
        """
        Return a list of all page names in this wiki.
        """
        return map(lambda x:x.Title,self.pages())

    security.declareProtected(Permissions.View, 'pageIdsStartingWith')
    def pageIdsStartingWith(self,text):
        """
        pageIdsStartingWith
        """
        return filter(lambda x:x[:len(text)]==text,self.pageIds())

    security.declareProtected(Permissions.View, 'pageNamesStartingWith')
    def pageNamesStartingWith(self,text):
        """
        pageNamesStartingWith
        """
        return filter(lambda x:x[:len(text)]==text,self.pageNames())

    security.declareProtected(Permissions.View, 'firstPageIdStartingWith')
    def firstPageIdStartingWith(self,text):
        """
        firstPageIdStartingWith
        """
        return (self.pageIdsStartingWith(text) or [None])[0]

    security.declareProtected(Permissions.View, 'firstPageNameStartingWith')
    def firstPageNameStartingWith(self,text):
        """
        firstPageNameStartingWith
        """
        return (self.pageNamesStartingWith(text) or [None])[0]

    security.declareProtected(Permissions.View, 'pageIdsMatching')
    def pageIdsMatching(self,text):
        """
        pageIdsMatching
        """
        text = text.lower()
        return filter(lambda x:x.lower().find(text)!=-1,self.pageIds())

    security.declareProtected(Permissions.View, 'pageNamesMatching')
    def pageNamesMatching(self,text):
        """
        pageNamesMatching
        """
        text = text.lower()
        return filter(lambda x:x.lower().find(text)!=-1,self.pageNames())

    security.declareProtected(Permissions.View, 'defaultPage')
    def defaultPage(self):
        """
        Return this wiki's default page object, where eg mail goes by default.

        That is:

        - a page named in the default_page string or lines property
        - or the page named FrontPage
        - or the first page object in the folder
        - or None.
        """
        # default_page property could be a list, tuple or string
        default_page_names = getattr(self.folder(),'default_page',[])
        if type(default_page_names) == StringType:
            default_page_names = [default_page_names]
        elif type(default_page_names) == TupleType:
            default_page_names = list(default_page_names)
        default_page_names.append('FrontPage')
        for name in default_page_names:
            p = self.pageWithName(name)
            if p: return p
        # pageObjects could be a LazyMap
        return (list(self.pageObjects())+[None])[0]

    security.declareProtected(Permissions.View, 'defaultPageId')
    def defaultPageId(self):
        """
        Return this wiki's default page ID.

        See defaultPage.
        """
        p = self.defaultPage()
        return (p and p.id()) or None

    security.declareProtected(Permissions.View, 'pageWithId')
    def pageWithId(self,id,url_quoted=0,ignore_case=0):
        """
        Return the page in this folder (or in the catalog) with this id.

        Can also do a case-insensitive id search, and optionally unquote
        id.  If no such page exists, return None.

        XXX if ALLBRAINS is set true below, this and all the methods based
        on it will return a page brain, not the actual page object.
        Rats.. enabling this actually slows down zwiki.org FrontPage
        rendering by 2.5 (due to extra catalog searching work ?) It should
        still perform better for many pages, small cache, low memory.. in
        theory.

        When link_to_all_cataloged is enabled, this will find any matching
        page in the catalog, regardless of physical location. As above, a
        brain will be returned, and performance implications are not known.

        """
        ALLBRAINS=0

        if id == None: return None # XXX review later
        if url_quoted: id = unquote(id)
        if self.linkToAllCataloged() or ALLBRAINS:
            page = self.pages(id=id) or (ignore_case and self.pages(id_nocase=id))
            return (page and page[0]) or None
        else:
            f = self.folder()
            # don't acquire
            # XXX special case: aq_base adds a REQUEST attribute
            # ('<Special Object Used to Force Acquisition>')
            if id in f.objectIds() and self.isZwikiPage(f[id]): # poor caching
                return f[id]
            elif ignore_case:
                id = string.lower(id)
                for i in self.pageIds():
                    if i.lower() == id:
                        return f[i]
            else:
                return None

    security.declareProtected(Permissions.View, 'pageWithName')
    def pageWithName(self,name,url_quoted=0):
        """
        Return the page in this folder which has this name, or None.

        page name may be different from page id, and if so is stored in
        the title property. Ie page name is currently defined as
        the value given by title_or_id().

        As of 0.17, page ids and names always follow the invariant
        id == canonicalIdFrom(name).

        To ease migration, we will also search for a page with the
        name utf-8-encoded.
        """
        return (self.pageWithId(self.canonicalIdFrom(name),url_quoted) or
                self.pageWithId(self.canonicalIdFrom(self.toencoded(name,'utf-8')),url_quoted))

    security.declareProtected(Permissions.View, 'pageWithNameOrId')
    def pageWithNameOrId(self,name,url_quoted=0):
        """
        Return the page in this folder with this as it's name or id, or None.
        """
        return (self.pageWithId(name,url_quoted) or
                self.pageWithName(name,url_quoted))

    security.declareProtected(Permissions.View, 'pageWithFuzzyName')
    def pageWithFuzzyName(self,name,url_quoted=0,allow_partial=0,
                          ignore_case=1, numeric_match=0):

        """
        Return the page in this folder for which name is a fuzzy link, or None.

        A fuzzy link ignores capitalization, punctuation and whitespace.
        If there are multiple fuzzy matches, return the page whose name is
        alphabetically first.

        The allow_partial flag allows even fuzzier matching. numeric_match
        modifies partial matching so that numbers match exactly, eg 1 does
        not match a page named 100.  ignore_case is not used and kept only
        for backward compatibility.

        performance-sensitive, at least the allow_partial=0 case
        """
        if url_quoted: name = unquote(name)

        # try common fast case first
        p = self.pageWithName(name)
        if p: return p

        # not quite as simple as you'd think
        id = self.canonicalIdFrom(name)
        idlower = id.lower()
        if allow_partial and name.isdigit():
            names = self.pageNames()
            names.sort()
            ids = [self.canonicalIdFrom(name) for name in names]
        else:
            ids = self.pageIds()

        for i in ids:
            ilower = i.lower()
            if (ilower == idlower or
                ((allow_partial and ilower[:len(idlower)] == idlower) and not
                 (numeric_match and re.match(r'[0-9]',ilower[len(idlower):])))
                ):
                return self.pageWithId(i)

        return None

    security.declareProtected(Permissions.View, 'backlinksFor')
    def backlinksFor(self, page):
        """
        Return metadata objects for all the pages that link to page.

        Optimisation: like pages(), this method used to return actual page
        objects but now returns metadata objects (catalog results if possible,
        or workalikes) to improve caching.

        page may be a name or id, and need not exist in the wiki

        The non-catalog search is not too smart.
        """
        p = self.pageWithNameOrId(page)
        if p:
            try: id = p.getId() # poor caching
            except AttributeError: id = p.id #all-brains
        else: id = page
        if self.hasCatalogIndexesMetadata(
            (['meta_type','path','canonicalLinks'], [])):
            return self.pages(canonicalLinks=id)
        else:
            # brute-force search (poor caching)
            # find both [page] and bare wiki links
            # XXX should check for fuzzy links
            # XXX should do a smarter search (eg use links())
            results = []
            linkpat = re.compile(r'\b(%s|%s)\b'%(page,id))
            for p in self.pageObjects():
                if linkpat.search(p.read()):
                    results.append(self.metadataFor(p))
            return results

    security.declareProtected(Permissions.View, 'translateHelper')
    def translateHelper(self,msgid,map=None):
        """
        When you want to translate a part of a sentence in a tag attribute,
        which is computed, you can not use i18n:attribute. and it's difficult
        to call _("") from the python: Expression.

        dont forget to force i18n extraction with something like

        <span tal:condition='nothing'>
            <!-- force i18n extraction -->
            <span title='Sentence' i18n:attributes='title'></span>
        </span>
        """

        translate_msg = _(msgid)
        if map:
            try:
                translate_msg = translate_msg % (map)
            except:
                return translate_msg
        return translate_msg

    ######################################################################
    # backwards compatibility

    # API methods for old skin templates
    security.declareProtected(Permissions.View, 'quickcomment')
    quickcomment = slowcomment = PageEditingSupport.comment
    security.declareProtected(Permissions.View, 'stxToHtml')
    stxToHtml = PageTypeStx().format
    src = PageEditingSupport.text
    editTimestamp = PageEditingSupport.timeStamp
    checkEditTimeStamp = PageEditingSupport.checkEditConflict
    wiki_page_url = PageUtils.page_url
    wiki_base_url = PageUtils.wiki_url
    zwiki_username_or_ip = PageUtils.usernameFrom
    applyLineEscapesIn = applyWikiLinkLineEscapesIn
    supportsEpoz = lambda x:False

    # CMF compatibility
    view = __call__

InitializeClass(ZWikiPage)


# rendering helper functions

def thunk_substituter(func, text):
    """Return a function which takes one arg and passes it with other args
    to passed-in func.

    thunk_substituter passes in a state dictionary: {'lastend': int,
    'inpre': bool, 'intag': bool}.  This is for use in a re.sub
    situation, to get the state into the callback.

    (The technical term really is "thunk".  Honest.-)"""
    state = {'lastend':0,'inpre':0,'incode':0,'intag':0,'inanchor':0}
    return lambda arg, func=func, text=text, state=state: func(arg,state,text)

def within_literal(upto, after, state, text,
                   rfind=rfind, lower=lower):
    """
    Check text from state['lastend'] to upto for literal context:

    - within an enclosing '<pre>' preformatted region '</pre>'
    - within an enclosing '<code>' code fragment '</code>'
    - within a tag '<' body '>'
    - within an '<a href...>' tag's contents '</a>'

    We also update the state dict accordingly.
    """
    # XXX This breaks on badly nested angle brackets and <pre></pre>, etc.
    lastend,inpre,incode,intag,inanchor = \
      state['lastend'], state['inpre'], state['incode'], state['intag'], \
      state['inanchor']

    newintag = newincode = newinpre = newinanchor = 0
    text = lower(text)

    # Check whether '<pre>' is currently (possibly, still) prevailing.
    opening = rfind(text, '<pre', lastend, upto)
    if (opening != -1) or inpre:
        if opening != -1: opening = opening + 4
        else: opening = lastend
        if -1 == rfind(text, '</pre>', opening, upto):
            newinpre = 1
    state['inpre'] = newinpre

    # Check whether '<code>' is currently (possibly, still) prevailing.
    opening = rfind(text, '<code', lastend, upto)
    if (opening != -1) or incode:
        if opening != -1: opening = opening + 5
        # We must already be incode, start at beginning of this segment:
        else: opening = lastend
        if -1 == rfind(text, '</code>', opening, upto):
            newincode = 1
    state['incode'] = newincode

    # Determine whether we're (possibly, still) within a tag.
    opening = rfind(text, '<', lastend, upto)
    if (opening != -1) or intag:
        # May also be intag - either way, we skip past last <tag>:
        if opening != -1: opening = opening + 1
        # We must already be intag, start at beginning of this segment:
        else: opening = lastend
        if -1 == rfind(text, '>', opening, upto):
            newintag = 1
    state['intag'] = newintag

    # Check whether '<a href...>' is currently (possibly, still) prevailing.
    #XXX make this more robust
    opening = rfind(text, '<a ', lastend, upto)
    got_anchor = opening != -1
    # we used to be looking for '<a href', but attribute order can
    # actually be the other way around, e.g. RST generating <a name=...
    href_too = False
    if got_anchor or inanchor: # found or already in anchor
        if got_anchor: # found it here
            # it might just have been <a name...>
            href_too = -1 != rfind(text, 'href', opening, upto)
            # if not href_too: opening = -1
        if opening != -1: opening = opening + 5
        else: opening = lastend
        got_anchor_closing = -1 == rfind(text, '</a>', opening, upto)
        if href_too and got_anchor_closing:
            newinanchor = 1 # the <a name=... href=...>WikiName</a> case
        elif got_anchor_closing:
            newinanchor = 0 # the <a name>WikiName</a> case
        # this would be: elif got_anchor and not got_anchor_closing:
            # the "<a name>WikiName - no closing" case is handled implicitly
            # newinanchor stays the same as initialized = 0
    state['inanchor'] = newinanchor

    state['lastend'] = after
    return newinpre or newincode or newintag or newinanchor

def withinSgmlOrDtml(span,text):
    """
    report whether the span lies inside an sgml or dtml tag in text
    """
    spans = sgmlAndDtmlSpansIn(text)
    for s in spans:
        if span[0] >= s[0] and span[1] <= s[1]:
            return 1
    return 0

def sgmlAndDtmlSpansIn(text):
    """
    return a list of spans (tuples) of all sgml and dtml tags in text
    """
    pat = re.compile(dtmlorsgmlexpr)
    spans = []
    lastpos = 0
    while 1:
        m = pat.search(text,lastpos)
        if not m:
            break
        else:
            s = m.span()
            spans.append(s)
            lastpos = s[1]
    return spans

def stripDelimitersFrom(link):
    """Strip a wiki link's enclosing [], [[]] or (())."""
    return re.sub(r'^(\[\[|\[|\(\()(.*?)(\]\]|\]|\)\))$',r'\2',link)


# ZMI page creation form
manage_addZWikiPageForm = DTMLFile('skins/zwiki/addwikipageform', globals())

def manage_addZWikiPage(self, name, REQUEST=None):
    """
    Add a new ZWiki Page to the current folder, in the ZMI.
    """
    # create page
    # this should be done in the proper order. Based on create()
    # XXX extract common method ?
    id = ZWikiPage().canonicalIdFrom(name)
    p = ZWikiPage(__name__=id)
    p.title=name
    newid = self._setObject(id,p)
    p = getattr(self,newid)
    p.setCreator(REQUEST)
    p.setLastEditor(REQUEST)
    p._setOwnership(REQUEST)
    p.setPageType(p.defaultPageType())
    p.setText('',REQUEST) # no harm
    #p.index_object() # should be no need
    p.wikiOutline().add(p.pageName())
    if REQUEST:
        if REQUEST.get('redirect','')=='page': u = p.pageUrl()
        else: u = REQUEST['URL1']+'/manage_main'
        REQUEST.RESPONSE.redirect(u)
