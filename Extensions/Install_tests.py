# Plone/CMF installation tests
# Actually these require Plone (for PloneTestCase ?)  and will be skipped
# if it is not present.

import unittest

from Products.ZWiki.CMF import HAS_PLONE

if not HAS_PLONE:
    def test_suite(): return unittest.TestSuite()

else:
    from Products.CMFPlone.tests import PloneTestCase

    from Products.ZWiki.Utils import safe_hasattr
    from Products.ZWiki.testsupport import ZopeTestCase, afterSetUp

    ZopeTestCase.installProduct('ZWiki')

    def install_via_external_method(site):
        site.manage_addProduct['ExternalMethod'].manage_addExternalMethod(
            'installzwiki','','ZWiki.Install','install')
        site.installzwiki(site)
                
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(Tests))
        return suite

    # this fixture provides a plone site without zwiki installed (XXX ?)
    class Tests(PloneTestCase.PloneTestCase):
        def afterSetUp(self):
            afterSetUp(self)
#             self.css        = self.portal.portal_css
#             self.js         = self.portal.portal_javascripts
#             self.skins      = self.portal.portal_skins
#             self.types      = self.portal.portal_types
#             self.properties = self.portal.portal_properties

        def test_install(self):
            portal_types = self.portal.portal_types
            t = 'Wiki Page'
            self.failIf(t in portal_types.objectIds())
            install_via_external_method(self.portal)
            self.failUnless(t in portal_types.objectIds())
