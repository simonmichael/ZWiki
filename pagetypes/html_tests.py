from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_html_page_type(self):
        self.p.edit(text='! PageOne PageTwo\n',type='html')
        self.assertEquals(self.p.render(bare=1),' PageOne PageTwo\n\n\n')
        self.p.edit(text='PageOne\n',type='html')
        self.assertEquals(
            self.p.render(bare=1),
            'PageOne<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=PageOne" title="create this page">?</a>\n\n\n')

