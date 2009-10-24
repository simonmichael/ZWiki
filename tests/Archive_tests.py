from testsupport import *
ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('ZCatalog')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_archiveFolder(self):
        p = self.page
        self.failIf(p.archiveFolder())
        p.ensureArchiveFolder()
        self.assert_(p.archiveFolder() is not None)
        self.assert_(p.archiveFolder().isPrincipiaFolderish)

