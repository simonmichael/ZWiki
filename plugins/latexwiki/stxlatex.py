import re
from types import *
from urllib import quote,unquote

from Products.ZWiki.Utils import BLATHER, formattedTraceback, html_quote
from Products.ZWiki.pagetypes import registerPageType, registerPageTypeUpgrade
from Products.ZWiki.pagetypes.common import *
from Products.ZWiki.pagetypes.stx import PageTypeStx
from Products.ZWiki.I18n import _

from util import defaultcharsizepx, workingDir, runCommand, findinpath
from ReplaceInlineLatex import replaceInlineLatex


class PageTypeStxLatex(PageTypeStx):
    """
    A page type like the Structured Text page type, with LaTeX support added.
    """
    _id = 'stxlatex'
    _name = 'Structured Text + LaTeX'
    supportsLaTeX = yes
    supportsPlone = yes

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+\
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        # Be more generous in STX for links...so they can contain equations
        t = re.sub(r'(^| )(?ms)"([^"]*)":(http://[-:A-Za-z0-9_,./\?=@#~&%()]*?)([.!?,;](?= )|(?= )|$)',\
            r'\1<a href="\3">\2</a>\4',t)
        # render latex
        # FIXME and the same for WikiLinks (harder)
        latexTemplate = None
        latexTemplatePage = getattr(page.folder(),
                                    'LatexTemplate', None)
        if latexTemplatePage:
            latexTemplate = latexTemplatePage.text()
        t = replaceInlineLatex(t, getattr(page.folder(),'latex_font_size',defaultcharsizepx), \
                                  getattr(page.folder(),'latex_align_fudge',0), 
                                  getattr(page.folder(),'latex_res_fudge',1.03), latexTemplate)
        # render stx
        t = self.format(t)
        t = page.markLinksIn(t)
        t = self.protectEmailAddresses(page,t)
        # add a CSS class to the whole thing
        t = '<div class="latexwiki">\n' + t + '\n</div>\n'
        return t

registerPageType(PageTypeStxLatex)
