from testsupport import *
ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('ZCatalog')
import transaction
from Products.ZWiki.Utils import sorted, base_hasattr

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

def isFolder(obj): return hasattr(obj,'isPrincipiaFolderish') and obj.isPrincipiaFolderish
def pageIds(folder): return sorted(list(folder.objectIds(spec='ZWiki Page')))
def pageCount(folder): return len(pageIds(folder))
def catalogedIds(page): return [b.id for b in page.pages()]
def hasCatalog(folder): return safe_hasattr(folder.aq_base, 'Catalog')
def hasOutline(folder): return safe_hasattr(folder.aq_base, 'outline')

class Tests(ZwikiTestCase):
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        # set up some prerequisites for archiving:
        # delete objects permission
        self.wiki.manage_permission(AccessControl.Permissions.delete_objects,['Anonymous'],acquire=0)
         # a _p_jar attribute for cut-paste
        transaction.get().savepoint()

    def test_archiveFolder(self):
        p = self.page
        self.failIf(p.archiveFolder())
        p.ensureArchiveFolder()
        self.assert_(p.archiveFolder() is not None)
        self.assert_(isFolder(p.archiveFolder()))

    def test_archive_one(self):
        p, f = self.page, self.wiki
        n = pageCount(f)
        p.archive()
        self.assertEqual(pageCount(p.archiveFolder()),1)
        self.assertEqual(pageCount(f),n-1)

    def test_archive_many(self):
        p, f = self.page, self.wiki
        # set up some children
        p.create('A')
        p.create('B')
        f.B.create('B1')
        f.B.create('B2')
        # and a sibling
        p.create('TestPage2')
        f.TestPage2.reparent(REQUEST=self.request)
        # B2 has a parent outside the archived tree
        f.B2.addParent('TestPage2')
        # make sure they all have a _p_jar
        transaction.get().savepoint()
        p.archive()
        self.assertEqual(set(pageIds(f)), set(['TestPage2','B2']))
        self.assertEqual(set(pageIds(p.archiveFolder())), set(['TestPage','A','B','B1']))
        # B2's parents list still refers to the archived page
        self.assertEqual(set(f.B2.getParents()), set(['B','TestPage2']))
        # but normal cleanup will take care of that
        f.B2.ensureValidParents()
        self.assertEqual(f.B2.getParents(), ['TestPage2'])

    def test_archive_and_catalog(self):
        p, f = self.page, self.wiki
        # should remove the archived page from the catalog
        p.ensureCatalog()
        p.archive()
        self.assertEqual([], catalogedIds(p))
        # should not create a catalog in the archive folder
        self.failIf(hasCatalog(p.archiveFolder()))

    def test_archive_and_outline(self):
        p, f = self.page, self.wiki
        # should remove the archived page from the outline cache
        p.ensureWikiOutline()
        p.archive()
        self.assertEqual([], p.wikiOutline().nodes())
        # should not create an outline cache in the archive folder
        self.failIf(hasOutline(p.archiveFolder()))

    def test_archive_and_revisions(self):
        p, f = self.page, self.wiki
        p.saveRevision()
        p.saveRevision()
        p.archive()
        af, rf = p.archiveFolder(), p.revisionsFolder()
        arf = af[p.getId()].revisionsFolder()
        # should have moved the revisions as well
        self.assertEqual(pageIds(rf), [])
        self.assert_(arf)
        self.assertEqual(set(pageIds(arf)), set(['TestPage.1','TestPage.2']))

    def test_accessing_main_folder_from_archive(self):
        p, f = self.page, self.wiki
        p.archive()
        self.assertEqual(f, p.archiveFolder().TestPage.wikiFolder())

