import os, sys
from Testing import ZopeTestCase
from Products.ZWiki.testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

class PageTypesTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_ZwikiStxPageType(self):
        self.p.edit(text='! PageOne PageTwo\n',type='stx')
        self.assertEquals(self.p.render(bare=1),
                          '<p> PageOne PageTwo</p>\n<p></p>\n')

    #def test_ZwikiRstPageType(self):
    #    self.p.edit(text='! PageOne PageTwo\n',type='msgrstprelinkdtmlfitissuehtml')
    #    self.assertEquals(
    #        self.p.render(bare=1),
    #        '<p> PageOne PageTwo</p>\n<p></p>\n')

    def test_ZwikiHtmlPageType(self):
        self.p.edit(text='! PageOne PageTwo\n',type='html')
        self.assertEquals(self.p.render(bare=1),' PageOne PageTwo\n\n')
        self.p.edit(text='PageOne\n',type='html')
        self.assertEquals(
            self.p.render(bare=1),
            'PageOne<a class="new" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=PageOne" title="create this page">?</a>\n\n')

    def test_ZwikiWwmlPageType(self):
        self.p.edit(text = \
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
""")
        self.assertEquals(self.p.render(bare=1),
"""
""")

    def test_ZwikiPlaintextPageType(self):
        self.p.folder().allowed_page_types = ['plaintext']
        self.p.edit(text='! PageOne PageTwo\n',type='plaintext')
        self.assertEquals(self.p.render(bare=1),
                          '<pre>\n! PageOne PageTwo\n\n</pre>\n\n')
        del self.p.folder().allowed_page_types



import unittest
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PageTypesTests))
    suite.level = 2
    return suite
