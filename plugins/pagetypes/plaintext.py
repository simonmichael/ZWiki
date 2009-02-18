from common import *
from Products.ZWiki.i18n import _
from Products.ZWiki.plugins.pagetypes import registerPageType

class PageTypePlaintext(PageTypeBase):
    _id = 'plaintext'
    _name = 'Plain text'

    def format(self,page,t):
        return "<pre>\n%s\n</pre>\n" % html_quote(t)

    def preRender(self, page, text=None):
        # a little different.. wrap document part in pre then run stx over the lot
        t = text or (self.format(page, page.document()) + '\n'+MIDSECTIONMARKER + \
                    self.preRenderMessages(page))
        t = self.obfuscateEmailAddresses(page,t)
        return t

    def discussionSeparator(self,page):
        return '\n<p>\n'

    def preRenderMessage(self,page,utfmsg):
        t = page.tounicode(utfmsg.get_payload())
        t = self.renderCitationsIn(page,t)
        t = self.format(page,t)
        t = self.addCommentHeadingTo(page,t,utfmsg)
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
