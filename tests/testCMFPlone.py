# This should be testInstall.py to correspond with Install.py, but we need
# a place for general CMF/Plone tests and may as well gather them here.
# Only tests specific to CMF and/or Plone should go in here; it's better
# to write a generic test elsewhere if possible.

import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *
ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('TextIndexNG2')

# we can no longer set up a test plone ourselves with plone 2 - rely on
# PloneTestCase instead.
# XXX Skip these tests if plone 2 & all required products are not present
# ? CMF still covered adequately ?
from Products.CMFPlone.tests import PloneTestCase

from testEditing import test_rename

def cmf_install_zwiki(site):
    site.manage_addProduct['ExternalMethod'].manage_addExternalMethod(
        'cmf_install_zwiki','','ZWiki.Install','install')
    site.cmf_install_zwiki()

# this fixture provides a plone site without zwiki installed
class CMFPloneInstallTests(PloneTestCase.PloneTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def testInstallViaExternalMethod(self):
        cmf_install_zwiki(self.portal)
        self.assert_(hasattr(self.portal.portal_types,'Wiki Page'))

    #def testInstallViaQuickInstaller(self):

# and this one comes with zwiki installed
class CMFPloneSpecificTests(PloneTestCase.PloneTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)
        # install zwiki and set the site up as our one-page test wiki
        # probably don't need to do this every time now
        cmf_install_zwiki(self.portal)
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
        #import pdb; pdb.set_trace()
        import ZPublisher
        t = ZPublisher.test('Zope',self.portal.TestPage.getPath())
        # can't make this work either.. TestPage seems to be disappearing
        # unexpectedly

    def testPageSaving(self):
        self.portal.TestPage.append(text='test')

    def test_setModificationDate(self):
        self.portal.TestPage.setModificationDate()

    testPageRenaming = test_rename

if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(CMFPloneInstallTests))
        suite.addTest(unittest.makeSuite(CMFPloneSpecificTests))
        return suite
