from Products.ZWiki.testsupport import *
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

