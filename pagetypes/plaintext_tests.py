from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_PageTypePlaintext(self):
        self.p.folder().allowed_page_types = ['plaintext']
        self.p.edit(text='! PageOne PageTwo\n',type='plaintext')
        self.assertEquals(self.p.render(bare=1),
                          '<pre>\n! PageOne PageTwo\n\n</pre>\n\n\n')
        del self.p.folder().allowed_page_types

