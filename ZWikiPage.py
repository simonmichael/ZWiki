"""
The main Zwiki module. See README.txt.

(c) 1999-2003 Simon Michael <simon@joyful.com> for the zwiki community.
Wikiwikiweb formatting by Tres Seaver <tseaver@zope.com>
Parenting code and regulations by Ken Manheimer <klm@zope.com>
Initial Zope CMF integration by Chris McDonough <chrism@zope.com>
Full credits are at http://zwiki.org/ZwikiContributors .

This product is available under the GNU GPL.  All rights reserved, all
disclaimers apply, etc.
"""
#style notes
#
# imports
#
#  are mostly in three groups: python, zope, zwiki
#
# docstrings
#
#  "The first line should always be a short, concise summary of the
#  object's purpose.  For brevity, it should not explicitly state the
#  object's name or type, since these are available by other means (except
#  if the name happens to be a verb describing a function's operation).
#  This line should begin with a capital letter and end with a period.
#
#  If there are more lines in the documentation string, the second line
#  should be blank, visually separating the summary from the rest of the
#  description.  The following lines should be one or more paragraphs
#  describing the object's calling conventions, its side effects, etc.
#
#  Data attributes override method attributes with the same name; to
#  avoid accidental name conflicts, which may cause hard-to-find bugs in
#  large programs, it is wise to use some kind of convention 
#  [such as] verbs for methods and nouns for data attributes."
#
# method visibility
#
#  naming with _ for privacy obscures the code, and so do excessive
#  security declarations. Omitting docstrings or documenting with comments
#  are not good either. Where a docstring is needed, I'm considering
#  putting it above the method name to indicate private methods, which
#  avoids these problems and makes it easy to change your mind.
#  Also sucks.
#

from __future__ import nested_scopes
import os, sys, re, string, time, thread
from string import split,join,find,lower,rfind,atoi,strip
from urllib import quote, unquote
from types import *

#import ZODB # need this for pychecker
from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import rfc1123_date
from DateTime import DateTime
import Globals
from OFS.DTMLDocument import DTMLDocument

import Permissions
from Defaults import AUTO_UPGRADE, \
     PAGE_METATYPE, LINK_TO_ALL_CATALOGED, LINK_TO_ALL_OBJECTS
from Regexps import url, bracketedexpr, doublebracketedexpr, \
     wikiname, wikilink, interwikilink, remotewikiurl, \
     protected_line, zwikiidcharsexpr, anywikilinkexpr, \
     markedwikilinkexpr, localwikilink, spaceandlowerexpr, \
     dtmlorsgmlexpr
from Utils import Utils, BLATHER
from UI import UI
from OutlineSupport import OutlineSupport
from Diff import DiffSupport
from Mail import MailSupport
from CatalogAwareness import CatalogAwareness
from Tracker import TrackerSupport
from CMF import CMFAwareness
from Fit import FitSupport
from Messages import MessagesSupport
from PurpleNumbers import PurpleNumbersSupport
from Admin import AdminSupport
from Editing import EditingSupport
from LocalizerSupport import LocalDTMLFile, _, N_
DTMLFile = LocalDTMLFile
del LocalDTMLFile

# these seem to need to be in this module or zope complains couldn't load state
#from PageTypes import MIDSECTIONMARKER,PAGETYPES,PAGE_TYPES
from PageTypes import MIDSECTIONMARKER, \
    ZwikiStxPageType, \
    ZwikiRstPageType, \
    ZwikiWwmlPageType, \
    ZwikiHtmlPageType, \
    ZwikiPlaintextPageType
PAGETYPES = [
    ZwikiStxPageType,
    ZwikiRstPageType,
    ZwikiWwmlPageType,
    ZwikiHtmlPageType,
    ZwikiPlaintextPageType,
    ]
# a dictionary of ids and names used by legacy skin templates
PAGE_TYPES = {}
for t in PAGETYPES: PAGE_TYPES[t._id]=t._name



class ZWikiPage(
    EditingSupport, # use our ftp/dav methods, not DTMLDocument's
    DTMLDocument,   # should DD really go last ?
    UI,
    OutlineSupport,
    DiffSupport,
    MailSupport,
    CatalogAwareness,
    TrackerSupport,
    CMFAwareness,
    FitSupport,
    MessagesSupport,
    PurpleNumbersSupport,
    AdminSupport,
    Utils,
    ):
    """
    A ZWikiPage is essentially a DTML Document which knows how to render
    itself in various wiki styles, and can function inside or outside a
    CMF site. A lot of extra methods are provided to support
    wiki-building, email, issue tracking, etc.

    Mixins are used to organize functionality into distinct modules.
    Initialization, rendering, editing and miscellaneous methods remain in
    the base class.

    """
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
    security.declareProtected(Permissions.Edit, 'manage_upload')
    security.declareProtected(Permissions.FTP, 'manage_FTPstat') # needed
    security.declareProtected(Permissions.FTP, 'manage_FTPlist') # ?
    # perms need at least one declaration (in this file ?) to be recognized
    security.declareProtected(Permissions.ChangeType, 'dummy')
    security.declareProtected(Permissions.Reparent, 'dummy')
    def dummy(self): pass 
    def checkPermission(self, permission, object):
        return getSecurityManager().checkPermission(permission,object)

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
        ) \
        + OutlineSupport._properties \
        + MailSupport._properties \
        + CatalogAwareness._properties

    meta_type = PAGE_METATYPE
    icon      = "misc_/ZWiki/ZWikiPage_icon"
    creator = ''
    creator_ip = ''
    creation_time = ''
    last_editor = ''
    last_editor_ip = ''
    last_edit_time = ''
    last_log = ''
    PAGE_TYPES = PAGE_TYPES # used by skin templates
    
    # page_type used to be a string used to select a render method. 
    # As of 0.25 it is an object which encapsulates the page's formatting
    # behaviour. It will return the old id string when called, which
    # should keep existing catalogs working.
    page_type = PAGETYPES[0]()
    def setPageType(self,id=None): self.page_type = self.lookupPageType(id)()
    def pageType(self):
        # I'd rather keep this in upgrade(), but someone might do
        # something requiring this before the page gets viewed
        if type(self.page_type) == StringType:
            BLATHER('upgraded page_type attribute of '+self.id())
            self.setPageType(self.page_type)
        return self.page_type
    def lookupPageType(self,id=None):
        match = filter(lambda x:x._id==id,PAGETYPES)
        return (match and match[0]) or PAGETYPES[0]
    def pageTypeId(self): return self.pageType().id()

    # pre-rendered text cache
    _prerendered = ''   
    def setPreRendered(self,t): self._prerendered = t
    def preRendered(self):
        # cope with non-existing or None attribute on old instances - needed ?
        return getattr(self,'_prerendered','') or ''

    ######################################################################
    # initialization

    def __init__(self, source_string='', mapping=None, __name__=''):
        """
        Initialise this instance, including it's CMF data if applicable.

        Ugly, but putting CMFAwareness before DTMLDocument in the
        inheritance order creates problems.
        """
        if self.supportsCMF():
            CMFAwareness.__init__(self,
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
    # rendering (see also the page type objects)

    security.declareProtected(Permissions.View, '__call__')
    def __call__(self, client=None, REQUEST={}, RESPONSE=None, **kw):
        """
        Render this zwiki page, upgrading it on the fly if needed

        Similar situation to __init__
        """
        if AUTO_UPGRADE: self.upgrade(REQUEST)
        if self.supportsCMF() and self.inCMF():
            return CMFAwareness.__call__(self,client,REQUEST,RESPONSE,**kw)
        else:
            rendered = self.render(client,REQUEST,RESPONSE,**kw)
            if RESPONSE:
                RESPONSE.setHeader('Content-Type', 'text/html')
                #RESPONSE.setHeader('Last-Modified', rfc1123_date(self._p_mtime)) 
                #causes browser caching problems ? 
            return rendered

    def render(self, client=None, REQUEST={}, RESPONSE=None, **kw):
        """
        Render the body of this zwiki page according to it's page_type
        """
        if not self.preRendered():
            self.setPreRendered(self.pageType().preRender(self))
        return self.pageType().render(self, REQUEST, RESPONSE, **kw)

    def preRender(self,clear_cache=0):
        """
        Make sure any applicable pre-rendering for this page has been done.
        
        If clear_cache is true, blow away any cached data.
        """
        if clear_cache: self.clearCache()
        get_transaction().note('prerender')
        self.setPreRendered(self.pageType().preRender(self))

    security.declareProtected(Permissions.View, 'clearCache')
    def clearCache(self,REQUEST=None):
        """
        forcibly clear out any cached render data for this page
        """
        self.setPreRendered('')
        if hasattr(self,'_v_cooked'):
            delattr(self,'_v_cooked')
            delattr(self,'_v_blocks')
        if REQUEST: REQUEST.RESPONSE.redirect(self.page_url())

    def cookDtmlIfNeeded(self):
        if self.dtmlAllowed() and self.hasDynamicContent(): self.cook()

    security.declareProtected(Permissions.View, 'cook')
    def cook(self, cooklock=thread.allocate_lock()):
        """
        Pre-parse this page's text (the pre-rendered, if available) for DTML.
        """
        cooklock.acquire()
        try:
            self._v_blocks=self.parse(self.preRendered() or self.read())
            self._v_cooked=None
        finally:
            cooklock.release()

    def evaluatePreRenderedAsDtml(self,client=None, REQUEST={},
                                  RESPONSE=None, **kw):
        # optimization: to save memory, avoid unnecessarily calling DTML
        # and generating _v_blocks data
        if not self.hasDynamicContent(): return self.preRendered()
        return DTMLDocument.__call__(self,client,REQUEST,RESPONSE,**kw)

    def renderMidsectionIn(self, text):
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
        return doc + self.renderMidsection() + discussion

    def renderMidsection(self):
        # XXX too expensive.. we calculate the wiki nesting info twice
        # per page view, once here and once for the navlinks in the header
        if self.subtopicsEnabled(): return self.subtopics(deep=1)
        else: return ''
    
    security.declareProtected(Permissions.View, 'supportsStx')
    def supportsStx(self): return self.pageType().supportsStx()

    security.declareProtected(Permissions.View, 'supportsRst')
    def supportsRst(self): return self.pageType().supportsRst()

    security.declareProtected(Permissions.View, 'supportsWwml')
    def supportsWwml(self): return self.pageType().supportsWwml()

    security.declareProtected(Permissions.View, 'supportsWikiLinks')
    def supportsWikiLinks(self): return self.pageType().supportsWikiLinks()

    security.declareProtected(Permissions.View, 'supportsHtml')
    def supportsHtml(self): return self.pageType().supportsHtml()

    security.declareProtected(Permissions.View, 'supportsDtml')
    def supportsDtml(self): return self.pageType().supportsDtml()

    security.declareProtected(Permissions.View, 'hasDynamicContent')
    def hasDynamicContent(self):
        return (self.supportsDtml() and
                re.search(r'(?i)(<dtml|&dtml)',self.read()) is not None)

    security.declareProtected(Permissions.View, 'dtmlAllowed')
    def dtmlAllowed(self): return (
        getattr(self,'allow_dtml',0) and
        not hasattr(self,'no_dtml')
        )

    security.declareProtected(Permissions.View, 'supportsEpoz')
    def supportsEpoz(self):
        return self.epozInstalled() and self.pageType().supportsEpoz()

    security.declareProtected(Permissions.View, 'epozInstalled')
    def epozInstalled(self):
        return hasattr(self,'Epoz')

    ######################################################################
    # link rendering and handling

    def isWikiName(self,name):
        """Is name a WikiName ?"""
        return re.match('^%s$' % wikiname,name) is not None

    def wikinameLinksAllowed(self):
        """Are wikinames linked in this wiki ?"""
        return getattr(self,'use_wikiname_links',1)

    def bracketLinksAllowed(self):
        """Are bracketed freeform names linked in this wiki ?"""
        return getattr(self,'use_bracket_links',1)

    def doublebracketLinksAllowed(self):
        """Are wikipedia-style double bracketed names linked in this wiki ?"""
        return getattr(self,'use_doublebracket_links',1)

    def hasAllowedLinkSyntax(self,link):
        if (re.match(url,link) or
            (self.wikinameLinksAllowed() and
             re.match(wikiname,link)) or
            (self.bracketLinksAllowed() and
             re.match(bracketedexpr,link) and
             not re.match(doublebracketedexpr,link)) or
            (self.doublebracketLinksAllowed() and
             re.match(doublebracketedexpr,link))):
            return 1
        else:
            return 0

    def markLinksIn(self,text):
        """
        Find and mark links in text, for fast replacement later.

        Successor to _preLink. Instead of generating a list of text
        extents and link names, this simply marks the links in place to
        make them easy to find again.  Tries to be smart about finding
        links only where you want it to.
        """
        #get_transaction().note('findlinks')
        markedtext = ''
        state = {'lastend':0,'inpre':0,'incode':0,'intag':0,'inanchor':0}
        lastpos = 0
        while 1:
            m = anywikilinkexpr.search(text,lastpos)
            if m:
                link = m.group()
                linkstart,linkend = m.span()
                if (link[0]=='!' or
                    not self.hasAllowedLinkSyntax(link) or
                    within_literal(linkstart,linkend-1,state,text) or
                    withinSgmlOrDtml((linkstart,linkend),text)):
                    # found the link pattern but it's escaped or disallowed or
                    # inside a STX quote or SGML tag - ignore (and strip the !)
                    if link[0] == '!': link=link[1:]
                    markedtext += text[lastpos:linkstart] + link
                else:
                    # a link! mark it and save it
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
        Find and render all links in text.
        """
        t = self.applyWikiLinkLineEscapesIn(text)
        t = re.sub(anywikilinkexpr,
                   thunk_substituter(self.renderLink, t, 1),
                   t)
        return t

    security.declareProtected(Permissions.View, 'wikilink')
    wikilink = renderLinksIn # api alias

    security.declareProtected(Permissions.View, 'applyWikiLinkLineEscapesIn')
    def applyWikiLinkLineEscapesIn(self, text):
        """
        implement wikilink-escaping in lines in text which begin with !
        """
        return re.sub(protected_line, self.protectLine, text)
        
    def protectLine(self, match):
        """
        return the string represented by match with all it's wikilinks escaped
        """
        return re.sub(wikilink, r'!\1', match.group(1))

    def renderLink(self,link,allowed=0,state=None,text='',
                   link_title=None,access_key=None):
        """
        Render a link depending on current wiki state.

        Can be called three ways:
        - directly (link should be a string)
        - from re.sub (link will be a match object, state will be None)
        - from re.sub via thunk substituter (state will be a dictionary) (old)
        """
        # preliminaries
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
        linkorig = link = re.sub(markedwikilinkexpr, r'\1', link)
        linknobrackets = re.sub(bracketedexpr, r'\1', link)

        # is this link escaped ?
        if link[0] == '!': return link[1:]

        # is it an interwiki link ?
        if re.match(interwikilink,link): return self.renderInterwikiLink(link)

        # is it something in brackets ?
        if re.match(bracketedexpr,link):
            # a STX footnote ? check for matching named anchor in the page text
            if re.search(r'(?s)<a name="ref%s"' % (re.escape(linknobrackets)),
                         text):
                return '<a href="%s#ref%s" title="footnote %s">[%s]</a>' \
                       % (self.page_url(),linknobrackets,
                          linknobrackets,linknobrackets)
            # or, an allowed bracketed freeform link syntax for this wiki ?
            if ((re.match(doublebracketedexpr,link) and
                 self.doublebracketLinksAllowed()) or
                (not re.match(doublebracketedexpr,link) and
                 self.bracketLinksAllowed())):
                # convert to a page id if possible, and continue
                p = self.pageWithFuzzyName(linknobrackets)
                if p:
                    try: link = p.getId() # XXX poor caching
                    except: link = p.id # all-brains
        
        # is it a bare URL ?
        if re.match(url,link):
            return '<a href="%s">%s</a>' % (link, link)

        # it must be a wikiname - are wikiname links allowed in this wiki ?
        if not (self.wikinameLinksAllowed() or
                re.match(bracketedexpr,linkorig)): #was processed above
            return link

        # we have a wikiname - does a matching page exist in this wiki ?
        if self.pageWithNameOrId(link):
            # the wikiname might not be the page id if international
            # characters have been enabled in wiki names but not page ids
            if not self.pageWithId(link):
                try: link = self.pageWithNameOrId(link).getId() # XXX poor caching
                except: link = self.pageWithNameOrId(link).id # all-brains
            linktitle = link_title or '' #self.pageWithId(link).linkTitle()
            accesskey = (access_key and ' accesskey="%s"' % access_key) or ''
            try: style=' style="background-color:%s;"' \
                   % self.pageWithNameOrId(link).issueColour() # poor caching
            except: style=' style="background-color:%s;"' \
                   % self.pageWithNameOrId(link).issueColour # all-brains
            return '<a href="%s/%s" title="%s"%s%s>%s</a>' \
                   % (self.wiki_url(),quote(link),linktitle,accesskey,
                      style,linknobrackets)

        # subwiki support: or does a matching page exist in the parent folder ?
        # XXX this is dumber than the above; doesn't handle i18n
        # characters, freeform names
        if (hasattr(self.folder(),'aq_parent') and
              hasattr(self.folder().aq_parent, link) and
              self.isZwikiPage(getattr(self.folder().aq_parent,link))): #XXX poor caching
            return '<a href="%s/../%s" title="page in parent wiki">../%s</a>'\
                   % (self.wiki_url(),quote(link),linkorig)

        # otherwise, provide a creation link
        return '%s<a class="new" href="%s/%s/createform?page=%s" title="create this page">?</a>' \
               % (linkorig, self.wiki_url(), quote(self.id()),
                  quote(linknobrackets))

    def renderInterwikiLink(self, link):
        """
        Render an occurence of interwikilink. link is a string.
        """
        if link[0] == '!': return link[1:]
        m = re.match(interwikilink,link)
        local, remote  = m.group('local'), m.group('remote')
        # check local is an allowed link syntax for this wiki
        if not self.hasAllowedLinkSyntax(local): return link
        local = re.sub(bracketedexpr, r'\1', local)
        # look for a RemoteWikiURL definition
        if hasattr(self.folder(), local): 
            m = re.search(remotewikiurl,getattr(self.folder(),local).text())
            if m:
                return '<a href="%s%s">%s:%s</a>' \
                       % (m.group('remoteurl'),remote,local,remote)
                       #XXX old html_unquote needed ? I don't think so
        # otherwise return unchanged
        return link

    security.declareProtected(Permissions.View, 'links')
    def links(self):
        """
        List the unique links occurring on this page - useful for cataloging.

        Includes urls & interwiki links but not structured text links.
        Extracts the marked links from prerendered data.  Does not
        generate this if missing - too expensive when cataloging ?
        """
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
                if link[0] == r'[' and link[-1] == r']':
                    link = link[1:-1]
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
                                  self.last_editor,
                                  prettyprint=prettyprint)

    # please clean me up
    security.declareProtected(Permissions.View, 'linkTitleFrom')
    def linkTitleFrom(self,last_edit_time=None,last_editor=None,prettyprint=0):
        """
        make a link title string from these last_edit_time and editor strings
        
        with prettyprint=1, format it for use in the standard header.
        """
        interval = self.asAgeString(last_edit_time)
        if not prettyprint:
            s = "last edited %s ago" % (interval)
        else:
            try:
                #XXX do timezone conversion ?
                lastlog = self.lastlog()
                if lastlog: lastlog = ' ('+lastlog+')'
                s = 'last edited <a href="%s/diff" title="show last edit%s">%s</a> ago' % \
                    (self.page_url(), lastlog, interval)
            except:
                s = 'last edited %s ago' % (interval)
        if (last_editor and
            not re.match(r'^[0-9\.\s]*$',last_editor)):
            # escape some things that might cause trouble in an attribute
            editor = re.sub(r'"',r'',last_editor)
            if not prettyprint:
                s = s + " by %s" % (editor)
            else:
                s = s + " by <b>%s</b>" % (editor)
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
        Return the name of this wiki page.

        This is normally in the title attribute, but use title_or_id
        to handle eg pages created in the ZMI.
        """
        return self.title_or_id()
    
    security.declarePublic('Title')
    def Title(self):
        return self.pageName()

    security.declareProtected(Permissions.View, 'canonicalIdFrom')
    def canonicalIdFrom(self,name):
        """
        Convert a free-form page name to a canonical url- and zope-safe id.

        Constraints for zwiki page ids:
        - it needs to be a legal zope object id
        - to simplify linking, we will require it to be a valid url
        - it should be unique for a given name (ignoring whitespace)
        - we'd like it to be as similar to the name and as simple to read
          and work with as possible
        - we'd like to encourage serendipitous linking between free-form
          and wikiname links & pages

        So this version
        - discards non-word-separating punctuation (')
        - converts remaining punctuation to spaces
        - capitalizes and joins whitespace-separated words into a wikiname
        - converts any non-zope-and-url-safe characters and _ to _hexvalue
        - if the above results in an id beginning with _, prepends X
          (XXX this breaks the uniqueness requirement, better ideas ?)

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
        if len(safeid) > 0 and safeid[0] == '_':
            safeid = 'X'+safeid
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

    security.declareProtected(Permissions.View, 'pages')
    def pages(self, **kw):
        """
        Look up metadata (brains) for some or all pages in this wiki.

        optimisation: prior to 0.22 this returned the actual page objects,
        but to help with caching efficiency it now uses the catalog, if
        possible.  The page metadata objects are catalog brains (search
        results) containing the catalog's metadata, or workalikes
        containing a limited number of fields and getObject().

        Warning: fields such as the parents list may be
        copies-by-reference, and should not be mutated.

        Any keyword arguments will be passed through to the catalog, for
        refining the search, sorting etc. When there is no catalog, only
        these arguments are supported: id, Title, text, and they do case
        insensitive partial matching.  With no arguments, all pages in the
        wiki are returned.

        With a partial catalog, ie a catalog which does not include all
        the metadata Zwiki expects, we'll get the missing fields from the
        zodb and add them to the catalog brains. In this case the
        catalog's caching advantage is lost.

        Different catalog configurations screw up our title and text
        searches somewhat. For the standard search form, we want: case
        insensitive, partial matching in page names and page text.
        
        """
        if self.hasCatalogIndexesMetadata((['meta_type','path'], [])):
            if self.linkToAllCataloged():
                # look at all cataloged pages ?
                return map(lambda x:self.ensureCompleteMetadataIn(x),
                           self.searchCatalog(meta_type=self.meta_type,
                                              **kw))
            else:
                # or (usually) just the ones in this folder
                wikipath = self.wikiPath()
                def folderpath(s): return s[:s.rfind('/')]
                return map(lambda x:self.ensureCompleteMetadataIn(x),
                           filter(lambda x:folderpath(x.getPath())==wikipath,
                                  self.searchCatalog(meta_type=self.meta_type,
                                                     path=wikipath,
                                                     **kw)))
        else:
            results = []
            for p in self.pageObjects(): results.append(self.metadataFor(p))
            # emulate (some) catalog arguments in a rudimentary way
            # these are all partial matching, case insensitive
            if kw:
                for arg in kw.keys():
                    value = kw[arg]
                    # catalog may use wildcards, but we won't
                    def stripWildCardsFrom(s):
                        try: return s.replace('*','')
                        except AttributeError: return s
                    value = stripWildCardsFrom(value)
                    if arg == 'text':
                        results = filter(
                            lambda x:find(x.getObject().text().lower(),
                                          value.lower()) != -1,
                            results)
                    if arg == 'id':
                        results = filter(
                            lambda x:find(x.id.lower(),value.lower()) != -1,
                            results)
                    if arg == 'Title':
                        results = filter(
                            lambda x:find(x.Title.lower(),value.lower()) != -1,
                            results)
                    #if arg == 'sort_order':
                    #if arg == 'sort_on':
            return results

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
        """
        #return self.folder().objectIds(spec=self.meta_type) # more robust ?
        return map(lambda x:x.id,self.pages())

    security.declareProtected(Permissions.View, 'pageNames')
    def pageNames(self):
        """
        Return a list of all page names in this wiki.
        """
        return map(lambda x:x.Title,self.pages())

    security.declareProtected(Permissions.View, 'pageIdsStartingWith')
    def pageIdsStartingWith(self,text):
        return filter(lambda x:x[:len(text)]==text,self.pageIds())

    security.declareProtected(Permissions.View, 'pageNamesStartingWith')
    def pageNamesStartingWith(self,text):
        return filter(lambda x:x[:len(text)]==text,self.pageNames())

    security.declareProtected(Permissions.View, 'firstPageIdStartingWith')
    def firstPageIdStartingWith(self,text):
        return (self.pageIdsStartingWith(text) or [None])[0]

    security.declareProtected(Permissions.View, 'firstPageNameStartingWith')
    def firstPageNameStartingWith(self,text):
        return (self.pageNamesStartingWith(text) or [None])[0]

    security.declareProtected(Permissions.View, 'pageIdsMatching')
    def pageIdsMatching(self,text):
        text = text.lower()
        return filter(lambda x:x.lower().find(text)!=-1,self.pageIds())

    security.declareProtected(Permissions.View, 'pageNamesMatching')
    def pageNamesMatching(self,text):
        text = text.lower()
        return filter(lambda x:x.lower().find(text)!=-1,self.pageNames())

    security.declareProtected(Permissions.View, 'defaultPage')
    def defaultPage(self):
        """
        Return this wiki's default page (object).
	
	That is the page named in the default_page property,
	or FrontPage,
        or the first page object in the folder, 
	or None.
        """
        return (
            self.pageWithName(getattr(self.folder,'default_page','FrontPage'))
            or (list(self.pageObjects())+[None])[0]) # pageObjects may be a LazyMap
        
    security.declareProtected(Permissions.View, 'defaultPageId')
    def defaultPageId(self):
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
            if hasattr(f.aq_base,id) and self.isZwikiPage(f[id]): # poor caching
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
        """
        return (self.pageWithId(self.canonicalIdFrom(name),url_quoted))

    security.declareProtected(Permissions.View, 'pageWithNameOrId')
    def pageWithNameOrId(self,name,url_quoted=0):
        """
        Return the page in this folder with this as it's name or id, or None.
        """
        return (self.pageWithId(name,url_quoted) or 
                self.pageWithName(name,url_quoted))
        
    security.declareProtected(Permissions.View, 'pageWithFuzzyName')
    def pageWithFuzzyName(self,name,url_quoted=0,
                          allow_partial=0,ignore_case=1):
        """
        Return the page in this folder for which name is a fuzzy link, or None.

        A fuzzy link ignores whitespace, case and punctuation.  If there
        are multiple fuzzy matches, return the page whose name is
        alphabetically first.  The allow_partial flag allows even fuzzier
        matching. As of 0.17 ignore_case is not used and kept only for
        backward compatibility.

        performance-sensitive
        """
        if url_quoted:
            name = unquote(name)
        p = self.pageWithName(name)
        if p: return p
        id = self.canonicalIdFrom(name)
        idlower = string.lower(id)
        ids = self.pageIds()
        # in case this is a BTreeFolder (& old zope ?), work around as per
        # IssueNo0535PageWithFuzzyNameAndBTreeFolder.. may not return
        # the alphabetically first page in this case
        try:
            ids.sort()
        except AttributeError:
            pass
        for i in ids:
            ilower = string.lower(i)
            if (ilower == idlower or 
                (allow_partial and ilower[:len(idlower)] == idlower)):
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
            except: id = p.id #all-brains
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

    ######################################################################
    # backwards compatibility

    security.declareProtected(Permissions.View, 'stxToHtml')
    # this must always be available, for the issue properties form
    def stxToHtml(self,t): return ZwikiStxPageType().renderStxIn(self,t)
    # CMF compatibility
    view = __call__
    SearchableText = EditingSupport.text
    # old API methods to help keep legacy DTML working
    src = EditingSupport.text
    editTimestamp = EditingSupport.timeStamp
    checkEditTimeStamp = EditingSupport.checkEditConflict
    #security.declareProtected(Permissions.View, 'wiki_page_url') # XXX need ?
    wiki_page_url = Utils.page_url
    wiki_base_url = Utils.wiki_url
    zwiki_username_or_ip = Utils.usernameFrom
    applyLineEscapesIn = applyWikiLinkLineEscapesIn 

Globals.InitializeClass(ZWikiPage)

# rendering helpers
def thunk_substituter(func, text, allowed):
    """Return a function which takes one arg and passes it with other args
    to passed-in func.

    thunk_substituter passes in the value of it's parameter, 'allowed', and a
    dictionary {'lastend': int, 'inpre': bool, 'intag': bool}.

    This is for use in a re.sub situation, to get the 'allowed' parameter and
    the state dict into the callback.

    (The technical term really is "thunk".  Honest.-)"""
    state = {'lastend':0,'inpre':0,'incode':0,'intag':0,'inanchor':0}
    return lambda arg, func=func, allowed=allowed, text=text, state=state: (
        func(arg, allowed, state, text))

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
    opening = rfind(text, '<pre>', lastend, upto)
    if (opening != -1) or inpre:
        if opening != -1: opening = opening + 4
        else: opening = lastend
        if -1 == rfind(text, '</pre>', opening, upto):
            newinpre = 1
    state['inpre'] = newinpre

    # Check whether '<code>' is currently (possibly, still) prevailing.
    opening = rfind(text, '<code>', lastend, upto)
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
    opening = rfind(text, '<a href', lastend, upto)
    if (opening != -1) or inanchor:
        if opening != -1: opening = opening + 5
        else: opening = lastend
        if -1 == rfind(text, '</a>', opening, upto):
            newinanchor = 1
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


# ZMI page creation form
manage_addZWikiPageForm = DTMLFile('dtml/zwikiPageAdd', globals())

def manage_addZWikiPage(self, id, title='', file='', REQUEST=None,
                        submit=None):
    """
    Add a ZWiki Page object with the contents of file.

    Usually zwiki pages are created by clicking on ? (via create); this
    allows them to be added in the standard ZMI way. These should give
    mostly similar results; refactor the two methods together if possible.
    """
    # create page and initialize in proper order, as in create.
    p = ZWikiPage(source_string='', __name__=id)
    newid = self._setObject(id,p)
    p = getattr(self,newid)
    p.title=title
    p.setCreator(REQUEST)
    p.setLastEditor(REQUEST)
    p._setOwnership(REQUEST)
    p.setPageType(getattr(self,'allowed_page_types',[None])[0])
    text = file
    if type(text) is not StringType: text=text.read()
    p.setText(text or '',REQUEST)
    p.wikiOutline().add(p.pageName()) # update the wiki outline
    p.index_object()
    if REQUEST is not None:
        try: u=self.DestinationURL()
        except: u=REQUEST['URL1']
        if submit==" Add and Edit ": u="%s/%s" % (u,quote(id))
        REQUEST.RESPONSE.redirect(u+'/manage_main')
    return ''

