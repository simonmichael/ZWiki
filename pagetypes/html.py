from common import *
from Products.ZWiki.I18nSupport import _

class ZwikiHtmlPageType(AbstractHtmlPageType):
    _id = 'html'
    _name = 'HTML'
    supportsHtml = yes
    supportsDtml = yes
    supportsEpoz = yes

    def preRender(self, page, text=None):
        t = text or (page.read()+'\n'+MIDSECTIONMARKER)
        t = page.applyWikiLinkLineEscapesIn(t)
        t = page.markLinksIn(t)
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        if page.dtmlAllowed() and page.hasDynamicContent():
            t = page.evaluatePreRenderedAsDtml(page,REQUEST,RESPONSE,**kw)
        else:
            t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        t = page.renderMidsectionIn(t)
        t = page.addSkinTo(t,**kw)
        return t

