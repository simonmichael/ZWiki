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
            ' new pages',
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
            ' changed pages',
            REQUEST=REQUEST)

    security.declareProtected(Permissions.View, 'rssForPages')
    def rssForPages(self, pages, title_suffix='', REQUEST=None):
        """Generate an RSS feed from the give page brains and title."""
        if len(pages) > 0:
            last_mod = pages[0].getObject().lastEditTime()
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
<description>%(last_log)s</description>
<pubDate>%(last_edit_time)s</pubDate>
</item>
""" % {
            'title':'[%s] %s' % (self.toencoded(self.title_quote(p.Title)),self.toencoded(self.title_quote(p.last_log))),
            'wikiurl':wikiurl,
            'id':p.id,
            'last_log':self.toencoded(html_quote(pobj.textDiff())),
            'last_edit_time':pobj.lastEditTime().rfc822(), # be robust here
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
