# MoinMoin-flavour Wiki-style markup
# contributed by Chad Miller <code@chad.org>
# extends WWML (or the misspelled WMML) to include MoinMoinIsms, approximately.

from common import *
from Products.ZWiki.I18nSupport import _
from Products.ZWiki.pagetypes import registerPageType

import re
import string
import urllib
from wwml import *


class ZwikiMoinPageType(AbstractPageType):
    _id = 'moin'
    _name = 'MoinMoin markup'
    supportsMoin = yes
    supportsWikiLinks = yes

    def renderMoinIn(self,t):
        return translate_MoinMoinML(html_quote(t))

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+\
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.renderMoinIn(t)
        if page.usingPurpleNumbers(): t = page.renderPurpleNumbersIn(t)
        t = page.markLinksIn(t)
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        if page.hasFitTests(): t = page.runFitTestsIn(t)
        if page.isIssue(): t = page.addIssueFormTo(t)
        t = page.renderMidsectionIn(t,**kw)
        t = page.addSkinTo(t,**kw)
        return t

registerPageType(ZwikiMoinPageType)


#  compatibility layer, for use until "WMML" spelling is finally corrected.
class WWMLTranslator(WMMLTranslator):
    pass

class MoinMoinMLTranslator(WWMLTranslator):

    # Add other protocols here?
    textlink      = re.compile( "\[(http://[^ ]+) ([^\[]+)\]" )

    header1Line   = re.compile( '^= (.*) =$' )
    header2Line   = re.compile( '^== (.*) ==$' )
    header3Line   = re.compile( '^=== (.*) ===$' )
    header4Line   = re.compile( '^==== (.*) ====$' )
    header5Line   = re.compile( '^===== (.*) =====$' )
    header6Line   = re.compile( '^====== (.*) ======$' )

    def replaceHeader1(self, matchObj): return self.replaceHeader( matchObj, 1 )
    def replaceHeader2(self, matchObj): return self.replaceHeader( matchObj, 2 )
    def replaceHeader3(self, matchObj): return self.replaceHeader( matchObj, 3 )
    def replaceHeader4(self, matchObj): return self.replaceHeader( matchObj, 4 )
    def replaceHeader5(self, matchObj): return self.replaceHeader( matchObj, 5 )
    def replaceHeader6(self, matchObj): return self.replaceHeader( matchObj, 6 )

    def replaceHeader( self, matchObj, number ):
        """
        Replace ^= text =$ with  <hN>text</hN>  , where N is the number 
	of '='s in a row.
        """
        return '<H%d>%s</H%d>' % ( number, matchObj.group(1), number )

    def replaceInlineTextlink( self, matchObj ):
        return '<A HREF="%s">%s</A>' % ( matchObj.group(1)
                                       , matchObj.group(2)
                                       )

    def mungeLine( self, line ) :
        """
        """
	line = WWMLTranslator.mungeLine(self, line)
        line        = self.textlink.sub( self.replaceInlineTextlink, line )
        line        = self.header1Line.sub( self.replaceHeader1, line )
        line        = self.header2Line.sub( self.replaceHeader2, line )
        line        = self.header3Line.sub( self.replaceHeader3, line )
        line        = self.header4Line.sub( self.replaceHeader4, line )
        line        = self.header5Line.sub( self.replaceHeader5, line )
        line        = self.header6Line.sub( self.replaceHeader6, line )
        return line


def translate_MoinMoinML( text ) :
    wt = MoinMoinMLTranslator()
    lines = wt( string.split( str( text ), '\n' ) )
    return string.join( lines, '\n' )

if __name__ == '__main__' :

    testString = \
"""
This is the first paragraph.  There should be a paragraph marker before it,
and it should wrap nicely around.

= Header 1 =

== header 2 ==

---------
That should have produced a horizontal rule.

The last word should be ''emphasized''.

The last word should be '''strong'''

Can we do both ''emph'' and '''strong''' on the same line?

How about two times:  ''emph1'' followed by ''emph2''?

   * one bullet, with a WikiName
   * second bullet, with an UnknownWikiName
      1. nested digit
      2. nested digit

   1. Top-level numbered list
   2. Top-level numbered list
      * nested bullet
      * nested bullet
   3. See if we keep the numbering here!

 Term: a definition
 ''Marked-up Term'': another definition, but with ''markup''
   : a definition without a term

  This should be monospaced,
    and indented manually

and now this is another normal paragraph.

 Here is some more pre-formatted text.
   * followed by a bullet

Let's see if AutomaticURLLinking works yet:
   * http://www.palladion.com
   * ftp://www.neosoft.com/pub/users/t/tseaver
   * mailto:tseaver@palladion.com
   * [http://web.chad.org/ Chad Miller] implementer of [http://twistedmatrix.com/users/jh.twistd/moin/moin.cgi/HelpOnEditing MoinMoin-similar code]

And [these words] should be linked, too.
"""
    class FakeParent :
        def __init__( self, parent, **kw ) :
            self.aq_parent = parent
            for key, value in kw.items() :
                setattr( self, key, value )

    grandparent = FakeParent( None, WikiName = 0 )
    print translate_MoinMoinML( testString )


