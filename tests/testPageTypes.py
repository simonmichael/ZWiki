import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

class PageTypesTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_ZwikiStxPageType(self):
        self.p.edit(text='! PageOne PageTwo\n',type='msgstxprelinkdtmlfitissuehtml')
        self.assertEquals(self.p.render(bare=1),
                          '<p> PageOne PageTwo</p>\n<p></p>\n')

    #def test_ZwikiRstPageType(self):
    #    self.p.edit(text='! PageOne PageTwo\n',type='msgrstprelinkdtmlfitissuehtml')
    #    self.assertEquals(
    #        self.p.render(bare=1),
    #        '<p> PageOne PageTwo</p>\n<p></p>\n')

    def test_ZwikiHtmlPageType(self):
        self.p.edit(text='! PageOne PageTwo\n',type='dtmlhtml')
        self.assertEquals(self.p.render(bare=1),' PageOne PageTwo\n\n')
        self.p.edit(text='PageOne\n',type='dtmlhtml')
        self.assertEquals(
            self.p.render(bare=1),
            'PageOne<a class="new" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=PageOne" title="create this page">?</a>\n\n')

    def test_ZwikiWwmlPageType(self):
        self.p.edit(text='! PageOne PageTwo\n',type='msgwwmlprelinkfitissue')
        #self.assertEquals(self.p.render(bare=1),'    PageOne PageTwo\n')
        # XXX temporary, due to midsection marker perhaps
        self.assertEquals(self.p.render(bare=1),'    PageOne PageTwo\n<P>\n')

    def test_ZwikiPlaintextPageType(self):
        self.p.folder().allowed_page_types = ['plaintext']
        self.p.edit(text='! PageOne PageTwo\n',type='plaintext')
        self.assertEquals(self.p.render(bare=1),
                          '<pre>\n! PageOne PageTwo\n\n</pre>\n\n')
        del self.p.folder().allowed_page_types


if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(PageTypesTests))
        return suite
