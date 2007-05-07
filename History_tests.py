from testsupport import *
ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('ZCatalog')

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
        rf = p.revisionsFolder()
        self.assert_(rf)
        self.assertEqual(p.revisionCount(), 2)
        self.assert_(hasattr(rf, p.getId()+'.1'))

        # should not require create permission
        self.folder.manage_permission('Zwiki: Add pages',[],acquire=0)
        # rely on test output, should test for some exception or condition
        p.saveRevision() 

        # should not update catalog in the wiki folder
        p.ensureCatalog()
        p.saveRevision()
        def catalogedids(p): return [b.id for b in p.pages()]
        self.assertEqual(['TestPage'], catalogedids(p))

        # should not create a catalog in the revisions folder
        self.failIf(hasattr(rf.aq_base, 'Catalog'))

        # nor update it if it happens to be there
        rev = rf['TestPage.1']
        rev.setupCatalog(reindex=0)
        p.saveRevision()
        self.assertEqual([], catalogedids(rev))
        
        # same thing for the outline cache -
        # should not update the one in the wiki folder
        p.ensureWikiOutline()
        p.saveRevision()
        self.assertEqual(['TestPage'], p.wikiOutline().nodes())

        # should not create one in the revisions folder
        self.failIf(hasattr(rf.aq_base, 'outline'))

        # should not update it if it's there
        rev.ensureWikiOutline()
        revoutline = rev.wikiOutline()
        revoutline.setParentmap({})
        self.assertEqual([], revoutline.nodes())
        p.saveRevision()
        self.assertEqual([], revoutline.nodes())

    def test_deleteMeSavesRevision(self):
        p = self.page
        p.handleDeleteMe('DeleteMe')
        self.assertEqual(p.revisionCount(), 2)

    def test_deleteSavesRevision(self):
        p = self.page
        p.delete()
        self.assertEqual(p.revisionCount(), 2)
