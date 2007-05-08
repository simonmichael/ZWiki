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
        self.assert_(p.revisionsFolder() is not None)
        self.assert_(p.revisionsFolder().isPrincipiaFolderish)

    def test_revisionCount(self):
        p = self.page
        self.assertEqual(p.revisionCount(), 1)

    def test_revisions(self):
        p = self.page
        self.assertEqual(1, len(p.revisions()))
        self.assertEqual(p, p.revisions()[0])
        p.edit(text='new text')
        self.assertEqual(2, len(p.revisions()))
        self.assertEqual(p.getId()+'.1', p.revisions()[0].getId())
        self.assertEqual(p, p.revisions()[1])
        
    def test_revisionNumber(self):
        p = self.page.folder()[self.page.create('NewPage')]
        self.assertEqual(p.revisionNumber(),         1)
        self.assertEqual(p.previousRevisionNumber(), None)
        self.assertEqual(p.nextRevisionNumber(),     None)

        p.edit(text='x')
        self.assertEqual(p.revisionNumber(),         2)
        self.assertEqual(p.previousRevisionNumber(), 1)
        self.assertEqual(p.nextRevisionNumber(),     None)

        p.edit(text='x')
        self.assertEqual(p.revisionNumber(),         3)
        self.assertEqual(p.previousRevisionNumber(), 2)
        self.assertEqual(p.nextRevisionNumber(),     None)

        # these work on the revision objects too
        revs = p.revisions()
        self.assertEqual(revs[0].revisionNumber(),         1)
        self.assertEqual(revs[0].previousRevisionNumber(), None)
        self.assertEqual(revs[0].nextRevisionNumber(),     2)

        self.assertEqual(revs[1].revisionNumber(),         2)
        self.assertEqual(revs[1].previousRevisionNumber(), 1)
        self.assertEqual(revs[1].nextRevisionNumber(),     3)

        self.assertEqual(revs[2].revisionNumber(),         3)
        self.assertEqual(revs[2].previousRevisionNumber(), 2)
        self.assertEqual(revs[2].nextRevisionNumber(),     None)

    def test_saveRevision(self):
        p = self.page
        r = p.revisionNumber()
        p.saveRevision()
        self.assertEqual(r+1, p.revisionNumber())
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

    def test_deleteSavesRevision(self):
        self.assert_('revisions' not in self.wiki.objectIds())
        self.page.delete()
        self.assert_('TestPage.1' in self.wiki.revisions.objectIds())

    def test_missingRevisions(self):
        # things should still work when revisions are deleted
        p = self.page
        p.append(text='x')
        p.append(text='x')
        p.append(text='x')

        self.assertEqual(p.revisionCount(), 4)
        self.assertEqual(p.previousRevisionNumber(), 3)
        self.assertEqual(p.revision(1).nextRevisionNumber(), 2)

        # delete revisions 2 and 3
        p.revisionsFolder().manage_delObjects(
            ids=[r.getId() for r in p.revisions()[1:3]])

        self.assertEqual(p.revisionCount(), 2)
        self.assertEqual(p.revisionNumber(), 4)
        self.assertEqual(p.previousRevisionNumber(), 1)
        self.assertEqual(p.revision(1).nextRevisionNumber(), 4)
        self.assertEqual(4, p.revision(4).revisionNumber())
        
