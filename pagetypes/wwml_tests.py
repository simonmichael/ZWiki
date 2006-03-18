from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_PageTypeWwml(self):
        self.p.edit(text = """
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
""")
        self.assertEquals(
            self.p.render(bare=1),
            """\
<p>This is the first paragraph.  There should be a paragraph marker before it,
and it should wrap nicely around.</p>
<p>---------
That should have produced a horizontal rule.</p>
<p>The last word should be ''emphasized''.</p>
<p>The last word should be '''strong'''</p>
<p>Can we do both ''emph'' and '''strong''' on the same line?</p>
<h2>How about two times:  ''emph1'' followed by ''emph2''?</h2>

<ul>
<li>one bullet, with a WikiName<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=WikiName" title="create this page">?</a>
        * second bullet, with an UnknownWikiName<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=UnknownWikiName" title="create this page">?</a>
                1. nested digit
                2. nested digit</li>

</ul>

<ol>
<li> Top-level numbered list
        2. Top-level numbered list
                <em> nested bullet
                </em> nested bullet
        3. See if we keep the numbering here!</li>

</ol>
<p>        Term: a definition
        ''Marked-up Term'': another definition, but with ''markup''
        : a definition without a term</p>
<p>  This should be monospaced,
    and indented manually</p>
<h2>and now this is another normal paragraph.</h2>
<p>  Here is some more pre-formatted text.
        * followed by a bullet</p>
<p>Let's see if AutomaticURLLinking<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=AutomaticURLLinking" title="create this page">?</a> works yet:
        <em> <a href="http://www.palladion.com">http://www.palladion.com</a>
        </em> <a href="ftp://www.neosoft.com/pub/users/t/tseaver">ftp://www.neosoft.com/pub/users/t/tseaver</a>
        * <a href="mailto:tseaver@palladion.com">mailto:tseaver@palladion.com</a></p>
<p>And [these words]<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=these%20words" title="create this page">?</a> should be linked, too.</p>
<p>
</p>
""")

