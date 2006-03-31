from common import *
from Products.ZWiki.I18n import _
from Products.ZWiki.pagetypes import registerPageType

# RST verbosity (MORE <- 0 debug, 1 info, 2 warning, 3 error, 4 severe -> LESS) :
RST_REPORT_LEVEL = 3
# top-level RST heading will render as this HTML heading:
RST_INITIAL_HEADER_LEVEL = 2

try:
    import reStructuredText # import this one first
except ImportError:
    reStructuredText = None
    BLATHER('could not import reStructuredText, will not be available')

class PageTypeRst(PageTypeBase):
    _id = 'rst'
    _name = 'reStructured Text'
    supportsRst = yes
    supportsWikiLinks = yes

    def format(self, t):
        if reStructuredText:
            return reStructuredText.HTML(
                t,
                report_level=RST_REPORT_LEVEL,
                initial_header_level=RST_INITIAL_HEADER_LEVEL-1
                )
        else:
            return "<pre>Error: could not import reStructuredText</pre>\n"+t

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+ \
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.format(t)
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

    def makeCommentHeading(self, page,
                           subject, username, time, 
                           message_id=None,in_reply_to=None):
        heading = '\n\n'
        heading += '| **%s** --' % (subject or '...')
        if username: heading = heading + '%s, ' % (username)
        heading += time
        heading += ' `%s <%s?subject=%s%s#bottom>`_' % (
            _("reply"),
            page.pageUrl(),
            quote(subject or ''),
            ((message_id and '&in_reply_to='+quote(message_id))
             or '')
            )
        heading += '\n| '
        return heading

    def discussionSeparator(self,page):
        return ''

    def inlineImage(self, page, id, path):
        return '\n\n.. image:: %s\n' % path
   
    def linkFile(self, page, id, path):
        return '\n\n!`%s`__\n\n__ %s\n' % (id, path)

registerPageType(PageTypeRst)

# backwards compatibility - need this here for old zodb objects
ZwikiRstPageType = PageTypeRst
