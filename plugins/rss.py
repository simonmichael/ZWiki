# zwiki RSS feed functionality

from __future__ import nested_scopes
from types import *
from urllib import quote, unquote
from DateTime import DateTime
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Products.ZWiki import Permissions
from Products.ZWiki.Utils import BLATHER, html_quote
from Products.ZWiki.i18n import _
from Products.ZWiki.plugins import registerPlugin

MAX_ITEM_DESC_SIZE = 1000

class PageRSSSupport:
    """
    I provide various kinds of RSS feed for the page and the whole wiki.
    """
    security = ClassSecurityInfo()

    security.declareProtected(Permissions.View, 'feedUrl')
    def feedUrl(self):
        return self.defaultPageUrl() + '/pages_rss'

    security.declareProtected(Permissions.View, 'pages_rss')
    def pages_rss(self, num=10, REQUEST=None):
        """Provide an RSS feed showing this wiki's recently created pages."""
        self.ensureCatalog()
        return self.rssForPages(
            self.pages(sort_on='creation_time',
                       sort_order='reverse',
                       sort_limit=num,
                       isBoring=0),
            lambda p: self.toencoded(self.title_quote(p.Title)),
            lambda p: p.creationTime(),
            lambda p: p.summary(MAX_ITEM_DESC_SIZE),
            ' new pages',
            REQUEST=REQUEST)

    security.declareProtected(Permissions.View, 'children_rss')
    def children_rss(self, num=10, REQUEST=None):
        """Provide an RSS feed listing this page's N most recently created
        direct children."""
        self.ensureCatalog()
        return self.rssForPages(
            self.pages(parents=self.pageName(),
                       sort_on='creation_time',
                       sort_order='reverse',
                       sort_limit=num,
                       isBoring=0),
            lambda p: self.toencoded(self.title_quote(p.Title)),
            lambda p: p.creationTime(),
            lambda p: p.summary(MAX_ITEM_DESC_SIZE),
            " %s child pages" % self.pageName(),
            REQUEST=REQUEST)

    security.declareProtected(Permissions.View, 'edits_rss')
    def edits_rss(self, num=10, REQUEST=None):
        """Provide an RSS feed listing this wiki's N most recently edited
        pages. May be useful for monitoring, as a (less detailed)
        alternative to an all edits mail subscription.
        """
        self.ensureCatalog()
        return self.rssForPages(
            self.pages(sort_on='last_edit_time',
                       sort_order='reverse',
                       sort_limit=num,
                       isBoring=0),
            lambda p: '[%s] %s' % (self.toencoded(self.title_quote(p.Title)), self.toencoded(self.title_quote(p.last_log))),
            lambda p: p.lastEditTime(),
            lambda p: html_quote(p.textDiff()),
            ' changed pages',
            REQUEST=REQUEST)

    security.declareProtected(Permissions.View, 'rssForPages')
    def rssForPages(self, pages, titlefunc, datefunc, descriptionfunc, title_suffix='', REQUEST=None):
        """Generate an RSS feed from the given page brains and
        title/date/description functions. titlefunc should take a page
        brain and return an item title string. datefunc should take a
        page object and return a DateTime object. descriptionfunc
        should take a page object and return a html-quoted string.
        """
        if len(pages) > 0:
            last_mod = datefunc(pages[0].getObject())
        else:
            last_mod = DateTime()
        if self.handle_modified_headers(last_mod=last_mod, REQUEST=REQUEST):
            return ''
        feedtitle = self.folder().title_or_id() + title_suffix
        feeddescription = feedtitle
        feedlanguage = 'en'
        feeddate = self.folder().bobobase_modification_time().rfc822()
        wikiurl = self.wikiUrl()
        if REQUEST: REQUEST.RESPONSE.setHeader('Content-Type','text/xml; charset=utf-8')
        t = """\
<rss version="2.0">
<channel>
<title>%(feedtitle)s</title>
<link>%(feedurl)s</link>
<description>%(feeddescription)s</description>
<language>%(feedlanguage)s</language>
<pubDate>%(feeddate)s</pubDate>
""" % {
            'feedtitle':self.toencoded(self.title_quote(feedtitle)),
            'feeddescription':self.toencoded(html_quote(feeddescription)),
            'feedurl':wikiurl,
            'feedlanguage':feedlanguage,
            'feeddate':feeddate,
            }
        for p in pages:
            pobj = p.getObject()
            t += """\
<item>
<title>%(title)s</title>
<link>%(wikiurl)s/%(id)s</link>
<guid>%(wikiurl)s/%(id)s</guid>
<description>%(description)s</description>
<pubDate>%(date)s</pubDate>
</item>
""" % {
            'title':titlefunc(p),
            'wikiurl':wikiurl,
            'id':p.id,
            'description':self.toencoded(descriptionfunc(pobj)),
            'date':datefunc(pobj).rfc822(), # be robust here
            }
        t += """\
</channel>
</rss>
"""
        return t

    def title_quote(self, title):
        """
        Quote a string suitable for a title element in an RSS feed.
        We replace only &, > and <
        this is according to RSS specs in
        http://www.rssboard.org/rss-profile#data-types-characterdata
        Nonetheless, http://feedvalidator.org/ claims there is html in 
        those encoded titles.
        """
        title = title.replace('&', '&#x26;', -1)
        title = title.replace('<', '&#x3C;', -1)
        title = title.replace('>', '&#x3E;', -1)
        return title

    # backwards compatibility
    changes_rss = edits_rss

InitializeClass(PageRSSSupport) 
registerPlugin(PageRSSSupport)
