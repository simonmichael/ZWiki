from support import *
#from ZCatalog import ZCatalog,Vocabulary
#from ZCatalog.Catalog import Catalog,CatalogError


class CatalogingTests(unittest.TestCase):
    # cf /usr/lib/zope/lib/python/Products/ZCatalog/tests/testCatalog.py
    #
    # we have various ZMI and zwiki methods
    # for adding, deleting, editing etc.
    # Easier to write doctests method by method ?
    #
    # these assume a default catalog is present and being used
    # beware of existing catalog data screwing things up, maybe
    # we can create our own (& set SITE_CATALOG) in zc

    def setUp(self):
        pass
    
    def tearDown(self):
        pass

#    def testOkWithoutCatalog(self):
#        pass

#    def testOkWithoutSiteCatalogProperty(self):
#        pass

#    def testCatalogingAwarenessWithZMIEdits(self):
#        pass
     
#    def testCatalogingAwarenessWithZWikiEdits(self):
#        zc = self.ZopeContext
#        assert not zc.Catalog(id='CatalogTestPage'), \
#               'uncreated page found in the catalog'
#        
#        zc.manage_addProduct['ZWiki'].manage_addZWikiPage('CatalogTestPage1')
#        zc.CatalogTestPage1.edit(page='CatalogTestPage',text='bleh')
#        assert zc.Catalog(id='CatalogTestPage'), \
#               'page not found in catalog after creation by edit'
#        assert zc.Catalog(PrincipiaSearchSource="bleh"), \
#               'page text not found in catalog after creation by edit'
#        assert not zc.Catalog(PrincipiaSearchSource="blib"), \
#               'dummy text found in catalog after creation by edit'
#
#        zc.CatalogTestPage.append(text='blib')
#        assert zc.Catalog(PrincipiaSearchSource="blib"), \
#               'new text not found in catalog after append'
#
#        zc.CatalogTestPage.edit(text='DeleteMe')
#        assert not hasattr(zc,'CatalogTestPage'), 'ack! page not deleted'
#        assert not zc.Catalog(id='CatalogTestPage'), \
#               'page still found in catalog after DeleteMe edit'
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CatalogingTests))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
