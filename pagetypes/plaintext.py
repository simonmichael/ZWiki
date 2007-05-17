from common import *
from Products.ZWiki.I18n import _
from Products.ZWiki.pagetypes import registerPageType

class PageTypePlaintext(PageTypeBase):
    _id = 'plaintext'
    _name = 'Plain text'

    def format(self,t):
        return "<pre>\n%s\n</pre>\n" % html_quote(t)

    def preRender(self, page, text=None):
        t = text or (page.document() + '\n'+MIDSECTIONMARKER + \
                    self.preRenderMessages(page))
        t = self.format(t)
        t = self.protectEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        if page.isIssue() and kw.get('show_issueproperties',1):
            t = page.addIssueFormTo(t)
        t = page.renderMidsectionIn(t,**kw)
        t = page.addSkinTo(t,**kw)
        return t

registerPageType(PageTypePlaintext)

# backwards compatibility - need this here for old zodb objects
ZwikiPlaintextPageType = PageTypePlaintext
