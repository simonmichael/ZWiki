from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_PageTypeRst(self):
        self.p.edit(text='! PageOne PageTwo\n',type='rst')
        self.assertEquals(
            self.p.render(bare=1),
            '<blockquote>\nPageOne PageTwo</blockquote>\n<p>\n</p>\n')

    def test_dtml_in_rst(self):
        p = self.p
        
        # disabled by default ?
        p.edit(text='<dtml-var "1+1">',type='rst')
        self.assert_(p.hasDynamicContent())
        self.assert_(not p.dtmlAllowed())
        self.assertEquals(
            p.render(bare=1),
            '<p>&lt;dtml-var &quot;1+1&quot;&gt;\n\n</p>\n')

        # can be enabled ?
        p.allow_dtml = 1
        self.assert_(p.dtmlAllowed())
        # XXX need both of these right here, why ?
        p.clearCache(); p.cook()
        self.assertEquals(p.render(bare=1), '2')

