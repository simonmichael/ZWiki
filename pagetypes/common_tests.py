from Products.ZWiki.tests.testsupport import *
#from Products.ZWiki.pagetypes.
from common import PageTypeBase
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_renderCitationsIn(self):
        p = self.page
        pagetype = p.lookupPageType('stx')()
        test = lambda x,y:self.assertEqual(pagetype.renderCitationsIn(p,x),y)
        # no citations
        test('a','a')
        # single level of citation
        test('> a\n','<blockquote type="cite">\na</blockquote>\n')
        # no terminating newline
        test('> a','<blockquote type="cite">\na</blockquote>\n')
        # double citation followed by single
        test('>> a\n> b\n',
             '<blockquote type="cite">\n<blockquote type="cite">\na</blockquote>\nb</blockquote>\n')
        # double with no following single
        test('>> a\n',
             '<blockquote type="cite">\n<blockquote type="cite">\na</blockquote>\n</blockquote>\n')

    def test_obfuscateEmailAddresses(self):
        f = lambda s:PageTypeBase().obfuscateEmailAddresses(self.p,s)
        self.assertEquals('abc', f('abc'))
        self.assertEquals('&#97;&#64;&#98;&#46;&#99;', f('a@b.c'))
        self.assertEquals('&#97;&#46;&#97;&#64;&#98;&#46;&#99;', f('a.a@b.c'))
        self.assertEquals('<a href="mailto:&#97;&#64;&#98;&#46;&#99;">&#97;&#64;&#98;&#46;&#99;</a>', f('<a href="mailto:a@b.c">a@b.c</a>'))
