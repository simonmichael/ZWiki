# MoinMoin-flavour Wiki-style markup
# copyright 2004 Simon Michael for the Zwiki community 
#
# MoinMoinMLTranslator contributed by Chad Miller <code@chad.org>
# extends WWML to include MoinMoinIsms, approximately.

from common import *
from Products.ZWiki.I18nSupport import _
from Products.ZWiki.pagetypes import registerPageType

from moin_support import render_moin_markup

class ZwikiMoinPageType(AbstractPageType):
    _id = 'moin'
    _name = 'MoinMoin markup'
    supportsMoin = yes
    supportsWikiLinks = yes

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+\
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.renderMoinIn(t)
        if page.usingPurpleNumbers(): t = page.renderPurpleNumbersIn(t)
        t = page.markLinksIn(t)
        t = self.protectEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        if page.hasFitTests(): t = page.runFitTestsIn(t)
        if page.isIssue() and kw.get('show_issueproperties',1):
            t = page.addIssueFormTo(t)
        t = page.renderMidsectionIn(t,**kw)
        t = page.addSkinTo(t,**kw)
        return t

    def renderMoinIn(self,t):
        return render_moin_markup(t)

registerPageType(ZwikiMoinPageType)
