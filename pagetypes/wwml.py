# WikiWikiWeb-style markup
# contributed by Tres Seaver <tseaver@palladion.com>

from common import *
from Products.ZWiki.I18nSupport import _
from Products.ZWiki.pagetypes import registerPageType

class ZwikiWwmlPageType(AbstractPageType):
    _id = 'wwml'
    _name = 'WikiWikiWeb markup'
    supportsWwml = yes
    supportsWikiLinks = yes

    def renderWwmlIn(self,t):
        return translate_WWML(html_quote(t))

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+\
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.renderWwmlIn(t)
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


# WWML formatter

name_pattern_1        = r'[A-Z]+[a-z]+[A-Z][A-Za-z]'
name_pattern_2        = r'[A-Z][A-Z]+[a-z][A-Za-z]'
bracket_pattern       = r'\[[\\\w.:_ ]+\]'

full_wikilink_pattern = re.compile( r'!?(%s*|%s*|%s)'
                                  % ( name_pattern_1
                                    , name_pattern_2
                                    , bracket_pattern
                                    )
                                  )

abbrev_wikilink_pattern = re.compile( r'!?(%s*|%s*)'
                                    % ( name_pattern_1
                                      , name_pattern_2
                                      )
                                    )

strip_bracket_pattern   = re.compile( r'^\[(.*)\]$' )

def Wiki_ize( self, text='', full_pattern=1 ):
    """
    Transform a html page into a wiki page by changing WikiNames
    into hyperlinks; pass full_pattern=1 to pick up square bracket
    links, too (default not to avoid fighting with StructuredText).
    """
    pattern = full_pattern and full_wikilink_pattern or abbrev_wikilink_pattern

    wikifier = _Wikifier( self )
    text = pattern.sub( wikifier._replaceWikilink, text )
    return text

class _Wikifier :

    def __init__( self, other ) :
        self.other_ = other

    def _replaceWikilink( self, matchobj ):
        """replace an occurrence of wikilink_pattern with a suitable hyperlink
        """
        # any matches preceded by ! should be left alone
        if re.match( '^!', matchobj.group( 0 ) ):
            return matchobj.group( 1 )

        # discard enclosing [] if any
        wikiname = strip_bracket_pattern.sub( r'\1', matchobj.group( 1 ) )

        # if something of this name exists, link to it;
        # otherwise, provide a "?" creation link
        if hasattr( self.other_.aq_parent, wikiname ): 
            return '<a href="../' + urllib.quote(wikiname) \
                 + '">' + wikiname + '</a>'
        else:
            return '%s<a href="%s/new?id=%s">?</a>' \
              % ( wikiname
                , urllib.quote( self.other_.id )
                , urllib.quote( wikiname ) )


class WWMLTranslator :
    """
    |FSM/translator for texts marked up using WikiWikiMarkupLanguage, as
    | defined at http://www.c2.org/cgi/wiki?TextFormattingRules:
    |
    |Paragraphs 
    |
    |    Don't Indent paragraphs 
    |
    |    Words wrap and fill as needed 
    |
    |    Use blank lines as separators 
    |
    |    Four or more minus signs make a horizontal rule 
    |
    |Lists 
    |
    |    tab-* for first level 
    |
    |        tab-tab-* for second level, etc. 
    |
    |    Use * for bullet lists, 1. for numbered lists (mix at will) 
    |
    |    tab-Term:-tab Definition for definition lists 
    |
    |    One line for each item 
    |
    |    Other leading whitespace signals preformatted text, changes font. 
    |
    |Fonts 
    |
    |    Indent with one or more spaces to use a monospace font: 
    |
    | This is in monospace # note it is off the margin
    |
    |This is not # it is on the left margin there
    |
    |Indented Paragraphs (Quotes) 
    |
    |    tab-space-:-tab -- often used (with emphasis) for quotations.
    |        (See SimulatingQuoteBlocks) 
    |
    |Emphasis 
    |
    |    Use doubled single-quotes ('') for emphasis (usually italics) 
    |
    |    Use tripled single-quotes (''') for strong emphasis (usually bold) 
    |
    |    Use five single-quotes ('), or triples within doubles, for some other
    |    kind of emphasis (BoldItalicInWiki), but be careful about the bugs in
    |    the Wiki emphasis logic... 
    |
    |    At most one per line. But as many as you need in a paragraph; just use
    |    multiple lines without intervening blank lines. 
    |
    |    Don't cross line boundaries 
    |
    |References 
    |
    |    JoinCapitalizedWords to make local references 
    |
    |    [1], [2], [3], [4] refer to remote references. Click EditLinks on the
    |    edit form to enter URLs 
    |
    |    Or precede URLs with "http:", "ftp:" or "mailto:" to create links
    |    automatically as in: http://c2.com/ 
    |
    |    URLs ending with .gif are inlined if inserted as a remote reference 
    |
    |    ISBN 0-13-748310-4 links to a bookseller. (The pattern is:
    |    "ISBN", optional colon, space, ten digits with optional hypens,
    |    the whole thing optionally in square brackets. The last digit can be
    |    an "X".) We are an AmazonAssociate. 
    |
    |        I S B N: 0123456789 becomes ISBN 0123456789 
    |        [I S B N 0123456789] becomes ISBN 0123456789 
    |        [I S B N: 123-456-789-X] becomes ISBN 123-456-789-X 
    """
    #
    #   Patterns used to parse markup.
    #
    blankLine     = re.compile( '^$' )
    anyGroup      = "(.*)"
    notTick       = "([^']*)"
    minimalMunch  = "(.*?)"
    strong        = re.compile( "'''%s'''" % minimalMunch )
    emphasis      = re.compile( "''%s''" % minimalMunch ) 
    forceBreak    = re.compile( r"\\\\" ) 
    hrule         = re.compile( '^----[-]*%s' % anyGroup )
    leadingSpaces = re.compile( '^( *)' )
    spaceChunks   = re.compile( ' {1,8}' )

    nTabs         = "([ \t]*)"
    tabList       = re.compile( '^%s%s' % ( nTabs, anyGroup ) )

    blockPrefix   = r'^(=)'
    tableFormat   = r'^\|(.*)\|'
    rowDivider    = r'\|'
    bulletPrefix  = r'^(\*)'
    digitPrefix   = r'^([0-9][0-9]*[\.]?)'
    dictPrefix    = "^([A-Za-z '-]*):"
    itemSuffix    = r"[ \t]+" + anyGroup

    blockItem     = re.compile( blockPrefix + itemSuffix )
    tableRow      = re.compile( tableFormat )
    tableDef      = re.compile( rowDivider )
    bulletItem    = re.compile( bulletPrefix + itemSuffix )
    digitItem     = re.compile( digitPrefix  + itemSuffix )
    dictItem      = re.compile( dictPrefix   + itemSuffix )

    codePrefix    = r'^([ \t]+)(?=[^*=|0] )'
    codeLine      = re.compile( codePrefix )

    httpPrefix    = '(http:)'
    ftpPrefix     = '(ftp:)'
    mailtoPrefix  = '(mailto:)'
    urlSuffix     = '([^ ]+)'

    httpURL       = re.compile( httpPrefix   + urlSuffix )
    ftpURL        = re.compile( ftpPrefix    + urlSuffix )
    mailtoURL     = re.compile( mailtoPrefix + urlSuffix )
    imageURL      = re.compile(
                    r'((?:http|ftp)://(?:.*?)\.(?:JPG|GIF|PNG|jpg|jpeg|gif|png))' 
                          )

#    def __init__( self, other ) :
    def __init__( self ) :
        """
        """
#        self.other              = other
        self.listStack          = []
        self.translatedLines    = []
        self.topList            = self.translatedLines
        self.topCode            = ''

    def nestingLevel( self ) :
        """
        How deep is the nesting stack?
        """
        return len( self.listStack )

    def pushList( self, code ) :
        """
        Start a new nested line list (e.g., for <UL>/<OL>/<DL>/<PRE>).
        """
        parentList   = self.topList
        self.topList = []
        self.topCode = code
        self.listStack.append( ( code, self.topList, parentList ) )


    def popList( self ) :
        """
        Finish current nested line list.
        """
        # First, pop the topmost record, and restore invariant (topList
        #  points to the list member of topmost).
        oldLevel                    = self.nestingLevel()
        if not oldLevel : return

        code, lines, self.topList   = self.listStack.pop()
        newLevel                    = self.nestingLevel()
        self.topCode = newLevel and self.listStack[ newLevel - 1 ][ 0 ] or ''

        # Next, insert popped record's lines as nested structure.
        if code == 'PRE' :
            indent = ''
        else :
            indent = '  '
        if code:
            self.topList.append( '%s<%s>' % ( indent, code ) )
        for line in lines :
            self.topList.append( '%s%s%s' % ( indent, indent, line ) )
        if code:
            self.topList.append( '%s</%s>' % ( indent, code ) )
    

    def replaceEmphasis( self, matchObj ) :
        """
        Replace ''foo'' with <EM>foo</EM>.
        """
        return '<EM>%s</EM>' % matchObj.group(1)
                               


    def replaceStrong( self, matchObj ) :
        """
        Replace '''foo''' with <STRONG>foo</STRONG>.
        """
        return '<STRONG>%s</STRONG>' % matchObj.group(1)

    def embedImage( self, matchObj ):
        return '<IMG SRC="%s">' % matchObj.group(1)

    def replaceInlineURL( self, matchObj ):
        """
        Replace http://www.foo.com with
             <A HREF="http://www.foo.com">http://www.foo.com</A>
             (likewise ftp: and mailto: URL's).
        """

        return '<A HREF="%s%s">%s%s</A>' % ( matchObj.group( 1 )
                                           , matchObj.group( 2 )
                                           , matchObj.group( 1 )
                                           , matchObj.group( 2 )
                                           )


    def appendCodeLine( self, line ) :
        """
        """
        while self.nestingLevel() > 1 :
            self.popList()

        if self.topCode != 'PRE' :
            self.popList()
            self.pushList( 'PRE' )

        self.topList.append( line )

    def mungeLine( self, line ) :
        """
        """
        #   Munge "simple" markup.
#        line        = Wiki_ize( self.other, line, 1 )
        line        = self.blankLine.sub( '<P>', line )
        line        = self.strong.sub( self.replaceStrong, line )
        line        = self.emphasis.sub( self.replaceEmphasis, line )
        line        = self.imageURL.sub( self.embedImage, line )
        # SKWM let the main routines take care of this later
        #line        = self.httpURL.sub( self.replaceInlineURL, line )
        #line        = self.ftpURL.sub( self.replaceInlineURL, line )
        #line        = self.mailtoURL.sub( self.replaceInlineURL, line )
        line        = self.hrule.sub( '<HR>', line )
        line        = self.forceBreak.sub( '<BR />', line )
        line        = self.blankLine.sub( '<P>', line )
        return line

    def parseLine( self, line ) :
        #   Break off leading tabs and count.
        tabMatch    = self.tabList.match( line )
        numTabs     = len( tabMatch.group( 1 ) )
        line        = tabMatch.group( 2 )

        #   Store line and compute new state.
        self.newState( numTabs, line )

    def replaceTableItems( self, matchObj ) :
        """
        """
        row = self.tableDef.sub("</TD><TD>", matchObj.group( 1 ))
        # return "<TR align=center><TD>%s</TD></TR>" % row
        return "<TR valign=top><TD>%s</TD></TR>" % row

    def insertBlockItem( self, matchObj ) :
        """
        """
        return "%s<BR />" % matchObj.group( 2 )

    def replaceListItem( self, matchObj ) :
        """
        """
        return "<LI> %s" % matchObj.group( 2 )

    def replaceDictItem( self, matchObj ) :
        """
        """
        return "<DT>%s<DD>%s" % ( matchObj.group( 1 ), matchObj.group( 2 ) )

    def lexListLine( self, line ) :

        line, nsub  = self.tableRow.subn( self.replaceTableItems, line )
        if nsub :
            return 'TABLE', self.mungeLine( line )

        line, nsub  = self.blockItem.subn( self.insertBlockItem, line )
        if nsub :
            return 'BLOCKQUOTE', self.mungeLine( line )

        line, nsub  = self.bulletItem.subn( self.replaceListItem, line )
        if nsub :
            return 'UL', self.mungeLine( line )

        line, nsub  = self.digitItem.subn( self.replaceListItem, line )
        if nsub :
            return 'OL', self.mungeLine( line )

        line, nsub  = self.dictItem.subn( self.replaceDictItem, line )
        if nsub :
            return 'DL', self.mungeLine( line )
        
        return '', self.mungeLine( line )

    def newState( self, numTabs, line ) :
        """
        Decode new state (i.e., adjust the nesting stack), based on
        current state and inputs.
        """
        level = self.nestingLevel()

        if self.topCode == 'PRE' :
            self.popList()

        if numTabs :
            newCode, line = self.lexListLine( line )
        else :
            newCode = ''
            line    = self.mungeLine( line )

        if level < numTabs :
            difference = numTabs - level
            for i in range(difference):
                self.pushList( newCode )
        elif level > numTabs :
            self.popList()
        
        if newCode != self.topCode :
            self.popList()
            if newCode :
                self.pushList( newCode )

        self.topList.append( line )


    def translate( self, lines ) :
        """
        """
        for line in lines :
            # PM: Turn leading spaces into tabs ... someone smarter than
            # me can figure out how to do this with a single regexp ...
            splitted = self.leadingSpaces.split(line)
            if len(splitted) == 3:
                line = self.spaceChunks.sub("\t", splitted[1]) + splitted[2]
            if self.codeLine.match( line ) :
                self.appendCodeLine( line )
            else :
                self.parseLine( line )
        return self.translatedLines
    
    __call__ = translate

#def translate_WWML( self, text ) :
#    wt = WWMLTranslator( self )
def translate_WWML( text ) :
    wt = WWMLTranslator()
    lines = wt( string.split( str( text ), '\n' ) )
    return string.join( lines, '\n' )

if __name__ == '__main__' :

    testString = \
"""
This is the first paragraph.  There should be a paragraph marker before it,
and it should wrap nicely around.

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

And [these words] should be linked, too.
"""
    class FakeParent :
        def __init__( self, parent, **kw ) :
            self.aq_parent = parent
            for key, value in kw.items() :
                setattr( self, key, value )

    grandparent = FakeParent( None, WikiName = 0 )
#    print translate_WWML( FakeParent( grandparent, id = 'parent' ), testString )
    print translate_WWML( testString )

registerPageType(ZwikiWwmlPageType)
