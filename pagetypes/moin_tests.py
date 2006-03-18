from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_moin_page_type(self):
        self.p.edit(text='! PageOne PageTwo\n',type='moin')
        self.assertEquals(
            self.p.render(bare=1),
            '<ul>\n<li style="list-style-type:none">\n<p>\nPageOne<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=PageOne" title="create this page">?</a> PageTwo<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=PageTwo" title="create this page">?</a> \n</p>\n</li>\n</ul>\n\n<p>\n\n \n</p>\n'
            )

