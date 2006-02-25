from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTests):

    def test_ZwikiRstPageType(self):
        self.p.edit(text='! PageOne PageTwo\n',type='msgrstprelinkdtmlfitissuehtml')
        self.assertEquals(
            self.p.render(bare=1),
            '<p> PageOne PageTwo</p>\n<p>\n</p>\n')

