from testsupport import *
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_revisionsFolder(self):
        p = self.page
        self.failIf(p.revisionsFolder())
        p.ensureRevisionsFolder()
        self.assert_(p.revisionsFolder())
        self.assert_(p.revisionsFolder().isPrincipiaFolderish)

    def test_revisionCount(self):
        p = self.page
        self.assertEqual(p.revisionCount(), 1)

    def test_revisions(self):
        p = self.page

        self.assertEqual(p.revisionCount(), 1)
        self.assertEqual(p.revisions()[-1].text(), p.text())

        p.edit(text='new text')
        self.assertEqual(p.revisionCount(), 2)
        self.assertEqual(p.revisions()[-1].text(), p.text())
        
    def test_revision(self):
        p = self.page
        self.assertEqual(p.revision(), 1)
        p.edit(text='new text')
        self.assertEqual(p.revision(), 2)
        self.assertEqual(p.revisions()[0].revision(), 1)
        self.assertEqual(p.revisions()[1].revision(), 2)

    def test_saveRevision(self):
        p = self.page
        p.saveRevision()
        self.assert_(p.revisionsFolder())
        self.assertEqual(p.revisionCount(), 2)
        self.assert_(hasattr(p.revisionsFolder(), p.getId()+'.1'))

    def test_deleteMeSavesRevision(self):
        p = self.page
        p.handleDeleteMe('DeleteMe')
        self.assertEqual(p.revisionCount(), 2)

    def test_deleteSavesRevision(self):
        p = self.page
        p.delete()
        self.assertEqual(p.revisionCount(), 2)
