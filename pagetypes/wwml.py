from common import *

from WWML import translate_WMML

class ZwikiWwmlPageType(AbstractPageType):
    _id = 'msgwwmlprelinkfitissue'
    _name = 'WikiWikiWeb markup'
    supportsWwml = yes
    supportsWikiLinks = yes

    def renderWwmlIn(self,t):
        return translate_WMML(html_quote(t))

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+\
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.renderWwmlIn(t)
        if page.usingPurpleNumbers(): t = page.renderPurpleNumbersIn(t)
        t = page.markLinksIn(t)
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        if page.hasFitTests(): t = page.runFitTestsIn(t)
        if page.isIssue(): t = page.addIssueFormTo(t)
        t = page.renderMidsectionIn(t)
        t = page.addSkinTo(t,**kw)
        return t

