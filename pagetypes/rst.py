from docutils.utils import new_document
from docutils.frontend import OptionParser
from docutils.parsers.rst import Parser
from docutils.nodes import section

from common import *
from Products.ZWiki.I18n import _
from Products.ZWiki.pagetypes import registerPageType

# RST verbosity (MORE <- 0 debug, 1 info, 2 warning, 3 error, 4 severe -> LESS) :
RST_REPORT_LEVEL = 4
# top-level RST heading will render as this HTML heading:
RST_INITIAL_HEADER_LEVEL = 2

try:
    import reStructuredText # import this one first
except ImportError:
    reStructuredText = None
    BLATHER('could not import reStructuredText, will not be available')

class PageTypeRst(PageTypeBase):
    """
    See also method docstrings in PageTypeBase.
    """
    _id = 'rst'
    _name = 'reStructured Text'
    supportsRst = yes
    supportsDtml = yes
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
        t = page.markLinksIn(t,urls=0)
        t = self.protectEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        if page.dtmlAllowed():
            t = page.evaluatePreRenderedAsDtml(page,REQUEST,RESPONSE,**kw)
        else:
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
        """
        Generate restructured text markup for a comment heading in a RST page.

        Our traditional comment layout - body immediately following
        heading with no blank line between - is possible in RST only if we
        had the comment body to play with, or by the solution used here:
        setting the class of the heading and first paragraph and using CSS
        to remove the margins.

        XXX NB this doesn't support complete styling as subsequent
        paragraphs don't have the class.  Things need to change so that
        comments are rendered from a template and can be fully customized
        using HTML+CSS, not the text markup rules.
        """
        heading = '\n\n.. class:: commentheading\n\n'
        heading += '**%s** --' % (subject or '...')
        if username: heading = heading + '%s, ' % (username)
        heading += time
        heading += ' `%s <%s?subject=%s%s#bottom>`_' % (
            _("reply"),
            page.pageUrl(),
            quote(subject or ''),
            ((message_id and '&in_reply_to='+quote(message_id))
             or '')
            )
        heading += '\n\n.. class:: commentbody\n\n'
        return heading

    def discussionSeparator(self,page):
        return ''

    def inlineImage(self, page, id, path):
        return '\n\n.. image:: %s\n' % path
   
    def linkFile(self, page, id, path):
        return '\n\n!`%s`__\n\n__ %s\n' % (id, path)

    # split and merge.. these are trickier than they seemed at first
    
    def split(self, page):
        """
        Move this page's top-level sections to sub-pages.

        Calls docutils to parse the text properly.
        Do we need to adjust heading styles ?
        """
        d = new_document(
            page.pageName(),
            OptionParser(components=(Parser,)).get_default_values())
        Parser().parse(page.text(), d)
        sections = [s for s in d.traverse() if isinstance(s,section)]
        # assume title is first element and body is the rest
        # create a sub-page for each section
        for s in sections:
            page.create(
                page=s[0].astext(),
                text=s.child_text_separator.join([p.astext() for p in s[1:]]))
        # leave just the preamble on the parent page
        page.edit(
            text=d.child_text_separator.join(
                [p.astext() for p in d[:d.first_child_matching_class(section)]]))
        
        if getattr(page,'REQUEST',None):
            page.REQUEST.RESPONSE.redirect(page.pageUrl())

    # XXX unfinished
    def merge(self, page):
        """
        Merge sub-pages as sections of this page.

        This merges all offspring, not just immediate children.
        """
        #get a rst parse tree of the current page
        d = new_document(
            page.pageName(),
            OptionParser(components=(Parser,)).get_default_values())
        Parser().parse(page.text(), d)
        #walk the offspring, adding as elements to the tree and deleting
        def walk(p):
            d2 = new_document(
                p.pageName(),
                OptionParser(components=(Parser,)).get_default_values())
            Parser().parse(p.text(), d2)
            d += d2.traverse()
            for c in page.childrenNesting():
                c = p.pageWithName(c)
                walk(c)
                c.delete()
        walk(page)
        #convert the tree back to source text and update this page
        page.edit(text=d.astext())

        #or: walk the offspring, adding as text to this page with
        #appropriate headings, and deleting
        #need to adjust headings ?
        #for p in page.offspringNesting():
        #    pass

        if getattr(page,'REQUEST',None):
            page.REQUEST.RESPONSE.redirect(page.pageUrl())

registerPageType(PageTypeRst)

# backwards compatibility - need this here for old zodb objects
ZwikiRstPageType = PageTypeRst
