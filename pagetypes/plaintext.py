from common import *
from Products.ZWiki.I18nSupport import _

class ZwikiPlaintextPageType(AbstractPageType):
    _id = 'plaintext'
    _name = 'Plain text'

    def renderPlaintextIn(self,t):
        return "<pre>\n%s\n</pre>\n" % html_quote(t)

    def preRender(self, page, text=None):
        t = text or page.read()
        t = self.renderPlaintextIn(t)
        if not text: t += '\n'+MIDSECTIONMARKER
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        t = page.renderMidsectionIn(t)
        t = page.addSkinTo(t,**kw)
        return t

