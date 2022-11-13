# Only tests specific to Plone and/or CMF should go in here; it's better
# to write a generic test elsewhere if possible.
#
# Actually these require Plone (for PloneTestCase ?)  and will be skipped
# if it is not present.
#
# XXX CMF covered adequately ?

from Products.ZWiki.CMF import HAS_PLONE

if not HAS_PLONE:
    import unittest
    def test_suite(): return unittest.TestSuite()

else:
    from Products.CMFPlone.tests import PloneTestCase

    from Products.ZWiki.Extensions.Install_tests import install_via_external_method
    from Editing_tests import test_rename
    from testsupport import *

    ZopeTestCase.installProduct('ZWiki')
    ZopeTestCase.installProduct('TextIndexNG2')

    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(Tests))
        return suite

    class Tests(PloneTestCase.PloneTestCase):
        def afterSetUp(self):
            afterSetUp(self)
            # install zwiki and set the site up as our one-page test wiki
            # probably don't need to do this every time now
            install_via_external_method(self.portal)
            self.wiki = self.portal
            self.portal.manage_addProduct['ZWiki'].manage_addZWikiPage('TestPage')
            self.page = self.portal.TestPage

        def XtestLinkToAllCataloged(self):
            # you're not allowed to shadow the id of an object in the portal
            # root folder (!) so we need to remove the outline object that
            # got created there during setup
            self.portal._delObject('outline')
            self.portal.manage_addFolder(id='folder1') #XXX Unauthorized ?
            self.portal.folder1.manage_addProduct['ZWiki'].manage_addZWikiPage('Page1')
            self.portal.manage_addFolder(id='folder2')
            self.portal.folder2.manage_addProduct['ZWiki'].manage_addZWikiPage('Page2')
            # off by default
            self.assert_(not self.page.linkToAllCataloged())
            self.assertEquals(len(self.page.pages()),1)
            # a property enables
            self.portal.link_to_all_cataloged = 1
            self.assert_(self.page.linkToAllCataloged())
            self.assertEquals(len(self.page.pages()),4)
            # (namely:
            # /portal/Members/test_user_1_/wiki/TestPage
            # /portal/TestPage
            # /portal/folder1/Page1
            # /portal/folder2/Page2)

        def XXXtestLinkToAllObjects(self):
            # off by default
            self.assert_(not self.page.linkToAllObjects())
            self.assertEquals(len(self.page.pages()),1)
            # a property enables
            self.portal.link_to_all_objects = 1
            self.assert_(self.page.linkToAllObjects())
            #self.assertEquals(len(self.page.pages()),1)

        def XXXtestPageViewing(self):
            #t = self.portal.index_html() # works
            #t = self.portal.TestPage() # fails, wants a CMF skin
            #app = ZopeTestCase.app()
            #ZopeTestCase.utils.setupSiteErrorLog(app)
            #ZopeTestCase.close(app)
            import ZPublisher
            t = ZPublisher.test('Zope',self.portal.TestPage.getPath())
            # can't make this work either.. TestPage seems to be disappearing
            # unexpectedly

        def testPageSaving(self):
            self.portal.TestPage.append(text='test')

        def test_setModificationDate(self):
            self.portal.TestPage.setModificationDate()

        testPageRenaming = test_rename

