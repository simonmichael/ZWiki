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

    # def test_revisionCount(self):
    #     p = self.page
    #     self.assertEqual(p.revisionCount(), 1)

    # def test_revisions(self):
    #     p = self.page
    #     self.assertEqual(1, len(p.revisions()))
    #     self.assertEqual(p, p.revisions()[0])
    #     p.edit(text='new text')
    #     self.assertEqual(2, len(p.revisions()))
    #     self.assertEqual(p.getId()+'.1', p.revisions()[0].getId())
    #     self.assertEqual(p, p.revisions()[1])
        
    # def test_revisionNumber(self):
    #     p = self.page.folder()[self.page.create('NewPage')]
    #     self.assertEqual(p.revisionNumber(),         1)
    #     self.assertEqual(p.previousRevisionNumber(), None)
    #     self.assertEqual(p.nextRevisionNumber(),     None)

    #     p.edit(text='x')
    #     self.assertEqual(p.revisionNumber(),         2)
    #     self.assertEqual(p.previousRevisionNumber(), 1)
    #     self.assertEqual(p.nextRevisionNumber(),     None)

    #     p.edit(text='x')
    #     self.assertEqual(p.revisionNumber(),         3)
    #     self.assertEqual(p.previousRevisionNumber(), 2)
    #     self.assertEqual(p.nextRevisionNumber(),     None)

    #     # these work on the revision objects too
    #     revs = p.revisions()
    #     self.assertEqual(revs[0].revisionNumber(),         1)
    #     self.assertEqual(revs[0].previousRevisionNumber(), None)
    #     self.assertEqual(revs[0].nextRevisionNumber(),     2)

    #     self.assertEqual(revs[1].revisionNumber(),         2)
    #     self.assertEqual(revs[1].previousRevisionNumber(), 1)
    #     self.assertEqual(revs[1].nextRevisionNumber(),     3)

    #     self.assertEqual(revs[2].revisionNumber(),         3)
    #     self.assertEqual(revs[2].previousRevisionNumber(), 2)
    #     self.assertEqual(revs[2].nextRevisionNumber(),     None)

    # def test_revisionNumbers(self):
    #     p = self.page
    #     self.assertEqual([1],p.revisionNumbers())
    #     p.edit(text='x')
    #     self.assertEqual([1,2],p.revisionNumbers())
        
        
    def test_archive(self):
        def pagecountin(f): return len(f.objectIds(spec='ZWiki Page'))
        p = self.page
        f = p.folder()

        self.assert_(not p.archiveFolder())
        p.ensureArchiveFolder()
        af = p.archiveFolder()
        self.assert_(af is not None)

        n = pagecountin(f)
        an = pagecountin(af)
        p.archive()
        self.assertEqual(pagecountin(f),n-1)
        self.assertEqual(pagecountin(af),an+1)

    #     # should not require create permission
    #     f.manage_permission('Zwiki: Add pages',[],acquire=0)
    #     # XXX failure here will only show up in test output, should fail the test
    #     f.manage_permission('Zwiki: Add pages',['Anonymous'],acquire=0)


    #     # should not update catalog in the wiki folder
    #     p.ensureCatalog()
    #     p.saveRevision()
    #     catalogedids = lambda p: [b.id for b in p.pages()]
    #     self.assertEqual(['TestPage'], catalogedids(p))

    #     # nor create one in the revisions folder
    #     self.failIf(safe_hasattr(rf.aq_base, 'Catalog'))

    #     # same thing for the outline cache -
    #     # should not update the one in the wiki folder
    #     p.ensureWikiOutline()
    #     p.saveRevision()
    #     self.assertEqual(['TestPage'], p.wikiOutline().nodes())

    #     # nore create one in the revisions folder
    #     self.failIf(safe_hasattr(rf.aq_base, 'outline'))

    #     # if revision object(s) already exist, jump to the next available number
    #     # when renaming..
    #     a = f[p.create('A')]
    #     self.assertEqual([1], a.revisionNumbers())
    #     b = f[p.create('B')]
    #     b.append(' ')
    #     b.append(' ')
    #     b.append(' ')
    #     rf['B.2'].delete()
    #     self.assertEqual([1,3,4], b.revisionNumbers())
    #     b.delete()
    #     a.rename('B')
    #     self.assertEqual([1,3,4,5], a.revisionNumbers())
    #     # or saving..
    #     b5 = ZWikiPage(__name__='B')
    #     b5.revision_number = 5
    #     rf._setObject('B.5', b5)
    #     b8 = ZWikiPage(__name__='B')
    #     b8.revision_number = 8
    #     rf._setObject('B.8', b8)
    #     a.append(' ')
    #     self.assertEqual([1,3,4,5,8,9,10], a.revisionNumbers())

    # def test_deleteSavesRevision(self):
    #     self.assert_('revisions' not in self.wiki.objectIds())
    #     self.page.delete()
    #     self.assert_('TestPage.1' in self.wiki.revisions.objectIds())

    # def test_missingRevisions(self):
    #     # things should still work when revisions are deleted
    #     p = self.page
    #     p.append(text='x')
    #     p.append(text='x')
    #     p.append(text='x')

    #     self.assertEqual(p.revisionCount(), 4)
    #     self.assertEqual(p.previousRevisionNumber(), 3)
    #     self.assertEqual(p.revision(1).nextRevisionNumber(), 2)

    #     # delete revisions 2 and 3
    #     p.revisionsFolder().manage_delObjects(
    #         ids=[r.getId() for r in p.revisions()[1:3]])

    #     self.assertEqual(p.revisionCount(), 2)
    #     self.assertEqual(p.revisionNumber(), 4)
    #     self.assertEqual(p.previousRevisionNumber(), 1)
    #     self.assertEqual(p.revision(1).nextRevisionNumber(), 4)
    #     self.assertEqual(4, p.revision(4).revisionNumber())
        
