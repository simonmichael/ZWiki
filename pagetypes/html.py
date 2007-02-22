from common import *
from Products.ZWiki.I18n import _
from Products.ZWiki.pagetypes import registerPageType

class PageTypeHtml(PageTypeBaseHtml):
    _id = 'html'
    _name = 'HTML'
    supportsHtml = yes
    supportsDtml = yes
    supportsEpoz = yes

    def preRender(self, page, text=None):
        t = text or (page.read()+'\n'+MIDSECTIONMARKER)
        t = page.applyWikiLinkLineEscapesIn(t)
        t = page.markLinksIn(t)
        t = self.protectEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        if page.dtmlAllowed() and page.hasDynamicContent():
            t = page.evaluatePreRenderedAsDtml(page,REQUEST,RESPONSE,**kw)
        else:
            t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        t = page.renderMidsectionIn(t,**kw)
        t = page.addSkinTo(t,**kw)
        return t

    def makeCommentHeading(self, page,
                           subject, username, time, 
                           message_id=None,in_reply_to=None):
        """
        Generate HTML markup for a comment heading in a HTML page.

        Note that we just work on the comment heading here. The content of the 
        comment is left as is, not certain what to do with it. Users likely 
        expect to be able to write comments like on every other page type
        (e.g. with two newlines to format paragraphs) - but what kind of markup
        would be expected on a html page? XXX
        """
        heading = '\n\n<p class="commentheading"> '
        heading += '<strong>%s</strong> --' % (subject or '...')
        if username: heading = heading + '%s, ' % (username)
        heading += time or ''
        heading += ' <a class="reference" href="%s?subject=%s%s#bottom">%s</a>' % (
            page.pageUrl(),
            quote(subject or ''),
            ((message_id and '&amp;in_reply_to='+quote(message_id))
             or ''),
            _("reply"),
            )
        heading += '\n\n</p>'
        return heading

registerPageType(PageTypeHtml)

# backwards compatibility - need this here for old zodb objects
ZwikiHtmlPageType = PageTypeHtml
