from common import *
from Products.ZWiki.I18nSupport import _
from Products.ZWiki.pagetypes import registerPageType

try:
    import reStructuredText # import this one first
    try:
        # start headings at level 2, not 3; will affect all rst clients
        # XXX not working
        import docutils.writers.html4zope
        docutils.writers.html4zope.default_level = 2
    except ImportError:
        # new zope 2.7.1, without html4zope
        pass
except ImportError:
    reStructuredText = None
    BLATHER('could not import reStructuredText, will not be available')

class ZwikiRstPageType(AbstractPageType):
    _id = 'rst'
    _name = 'reStructured Text'
    supportsRst = yes
    supportsWikiLinks = yes

    def renderRstIn(self,t):
        if reStructuredText:
            return reStructuredText.HTML(t,report_level=0) # doesn't work:(
        else:
            return "<pre>Error: could not import reStructuredText</pre>\n"+t

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+ \
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.renderRstIn(t)
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

    def makeCommentHeading(self, page,
                           subject, username, time, 
                           message_id=None,in_reply_to=None):
        heading = '\n\n'
        heading += '**%s** --' % (subject or '...')
        if username: heading = heading + '`%s`, ' % (username)
        heading += time
        heading += ' `%s`__\n\n' % _("reply")
        if message_id:
            inreplytobit = '&in_reply_to='+quote(message_id)
        else:
            in_reply_to = ''
        heading += '__ %s?subject=%s%s#bottom\n\n' % (page.page_url(),
                                                      quote(subject or ''),
                                                      inreplytobit)
        return heading

    def discussionSeparator(self,page):
        return '\n\n-----\n\n'

    def inlineImage(self, page, id, path):
        return '\n\n.. image:: %s\n' % path
   
    def linkFile(self, page, id, path):
        return '\n\n!`%s`__\n\n__ %s\n' % (id, path)

registerPageType(ZwikiRstPageType)
