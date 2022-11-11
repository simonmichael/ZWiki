import sys

from docutils.utils import new_document
from docutils.frontend import OptionParser
from docutils.parsers.rst import Parser
from docutils.nodes import section
from docutils.core import publish_parts

# Disable inclusion of files for security reasons.  We do this by
# changing the default value of the ``file_insertion_enabled``
# parameter to False.
import docutils.parsers.rst
for title, options, conf in docutils.parsers.rst.Parser.settings_spec[2]:
    if options == ['--file-insertion-enabled']:
        conf['default'] = 0
        break

from common import *
from Products.ZWiki.i18n import _
from Products.ZWiki.plugins.pagetypes import registerPageType

# RST verbosity (MORE <- 0 debug, 1 info, 2 warning, 3 error, 4 severe -> LESS) :
RST_REPORT_LEVEL = 4
# top-level RST heading will render as this HTML heading:
RST_INITIAL_HEADER_LEVEL = 2


class PageTypeRst(PageTypeBase):
    """
    See also method docstrings in PageTypeBase.
    """
    _id = 'rst'
    _name = 'reStructured Text'
    supportsRst = yes
    supportsDtml = yes
    supportsWikiLinks = yes

    def format(self, page, t):
        # rst returns an encoded string.. decode it back to unicode
        # hopefully the rst encoding in zope.conf matches the wiki's encoding
        return page.tounicode(HTML(
                t,
                report_level=RST_REPORT_LEVEL,
                initial_header_level=RST_INITIAL_HEADER_LEVEL-1,
                settings={'raw_enabled':getattr(page,'rst_raw_enabled',0) and 1}
                ))

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+ \
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.format(page,t)
        t = page.markLinksIn(t,urls=0)
        t = self.obfuscateEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        if page.dtmlAllowed():
            t = page.evaluatePreRenderedAsDtml(page,REQUEST,RESPONSE,**kw)
        else:
            t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
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
        heading += '**%s** --' % (page.tounicode(subject) or '...')
        if username: heading = heading + '%s, ' % (page.tounicode(username))
        heading += time
        subject    = subject or ''
        message_id = message_id or ''
        heading += ' `%s <%s?subject=%s%s#bottom>`_' % (
            _("reply"),
            page.pageUrl(),
            quote(subject or ''),
            ((message_id and '&in_reply_to='+quote(message_id)) or '')
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


# Zope4 has dropped reStructuredText package. We call docutils directly,
# based on the last revision of the 2.13 branch:
# https://github.com/zopefoundation/Zope/tree/2.13/src/reStructuredText/
# __init__.py)
# with the following changes:
# * let the "settings" argument of "render()" override the default
#   values: https://bugs.launchpad.net/zope2/+bug/143852
# * no more settings from Zope configuration:
#   - rest_{input|output}_encoding => use 'unicode' instead
#   - rest_header_level => 3 (we use h3 as default)
#   - rest_language_code => en (we use english as default)
#  XXX: for the last two (level and lang) we should provide an override
#       mechanism

class Warnings:

    def __init__(self):
        self.messages = []

    def write(self, message):
        self.messages.append(message)

# starting level for <H> elements (default behaviour inside Zope is <H3>)
default_level = 3
initial_header_level = default_level

# default language used for internal translations and language mappings for DTD
# elements
default_lang = 'en'
default_language_code = default_lang


def render(src,
           writer='html4css1',
           report_level=1,
           stylesheet=None,
           language_code=default_language_code,
           initial_header_level = initial_header_level,
           settings = {}):
    """get the rendered parts of the document the and warning object
    """
    # Docutils settings:
    allsettings = {}
    allsettings['file_insertion_enabled'] = 0
    allsettings['raw_enabled'] = 0
    # don't break if we get errors:
    allsettings['halt_level'] = 6
    # remember warnings:
    allsettings['warning_stream'] = warning_stream = Warnings()
    # now update with user supplied settings
    allsettings.update(settings)
    # and then add settings based on keyword parameters
    allsettings['input_encoding'] = 'unicode'
    allsettings['output_encoding'] = 'unicode'
    allsettings['stylesheet'] = stylesheet
    allsettings['stylesheet_path'] = None
    allsettings['language_code'] = language_code
    # starting level for <H> elements:
    allsettings['initial_header_level'] = initial_header_level + 1
    # set the reporting level to something sane:
    allsettings['report_level'] = report_level

    # make sure that ``source`` is a unicode object
    assert type(src) == unicode

    parts = publish_parts(source=src, writer_name=writer,
                          settings_overrides=allsettings,
                          config_section='zope application')

    return parts, warning_stream

def HTML(src,
         writer='html4css1',
         report_level=1,
         stylesheet=None,
         language_code=default_language_code,
         initial_header_level = initial_header_level,
         warnings = None,
         settings = {}):
    """ render HTML from a reStructuredText string

        - 'src'  -- string containing a valid reST document

        - 'writer' -- docutils writer

        - 'report_level' - verbosity of reST parser

        - 'stylesheet' - Stylesheet to be used

        - 'report_level' - verbosity of reST parser

        - 'language_code' - docutils language

        - 'initial_header_level' - level of the first header tag

        - 'warnings' - will be overwritten with a string containing the warnings

        - 'settings' - dict of settings to pass in to Docutils, with priority

    """
    parts, warning_stream = render(src,
                                   writer = writer,
                                   report_level = report_level,
                                   stylesheet = stylesheet,
                                   language_code=language_code,
                                   initial_header_level = initial_header_level,
                                   settings = settings)

    header = '<h%(level)s class="title">%(title)s</h%(level)s>\n' % {
                  'level': initial_header_level,
                  'title': parts['title'],
             }

    subheader = '<h%(level)s class="subtitle">%(subtitle)s</h%(level)s>\n' % {
                  'level': initial_header_level+1,
                  'subtitle': parts['subtitle'],
             }

    body = '%(docinfo)s%(body)s' % {
                  'docinfo': parts['docinfo'],
                  'body': parts['body'],
             }


    output = ''
    if parts['title']:
        output = output + header
    if parts['subtitle']:
        output = output + subheader
    output = output + body


    warnings = ''.join(warning_stream.messages)

    return output
