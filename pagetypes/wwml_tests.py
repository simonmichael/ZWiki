from Products.ZWiki.testsupport import *
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def afterSetUp(self):
        afterSetUp(self)
        self.p.edit(type='wwml')

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
<P>
This is the first paragraph.  There should be a paragraph marker before it,
and it should wrap nicely around.
<P>
<HR>
That should have produced a horizontal rule.
<P>
The last word should be <EM>emphasized</EM>.
<P>
The last word should be <STRONG>strong</STRONG>
<P>
Can we do both <EM>emph</EM> and <STRONG>strong</STRONG> on the same line?
<P>
How about two times:  <EM>emph1</EM> followed by <EM>emph2</EM>?
<P>
  <UL>
    <LI> one bullet, with a WikiName<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=WikiName" title="create this page">?</a>
    <LI> second bullet, with an UnknownWikiName<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=UnknownWikiName" title="create this page">?</a>
      <OL>
        <LI> nested digit
        <LI> nested digit
      </OL>
  </UL>
<P>
  <OL>
    <LI> Top-level numbered list
    <LI> Top-level numbered list
      <UL>
        <LI> nested bullet
        <LI> nested bullet
      </UL>
    <LI> See if we keep the numbering here!
  </OL>
<P>
  <DL>
    <DT>Term<DD>a definition
    <DT><EM>Marked-up Term</EM><DD>another definition, but with <EM>markup</EM>
  </DL>
<PRE>
	: a definition without a term
</PRE>
<P>
    This should be monospaced,
    and indented manually
<P>
and now this is another normal paragraph.
<P>
    Here is some more pre-formatted text.
  <UL>
    <LI> followed by a bullet
  </UL>
<P>
Let's see if AutomaticURLLinking<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=AutomaticURLLinking" title="create this page">?</a> works yet:
  <UL>
    <LI> <a href="http://www.palladion.com">http://www.palladion.com</a>
    <LI> <a href="ftp://www.neosoft.com/pub/users/t/tseaver">ftp://www.neosoft.com/pub/users/t/tseaver</a>
    <LI> <a href="mailto:tseaver@palladion.com">mailto:tseaver@palladion.com</a>
  </UL>
<P>
And [these words]<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=these%20words" title="create this page">?</a> should be linked, too.
<P>

""")

