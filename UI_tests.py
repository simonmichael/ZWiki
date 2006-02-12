import unittest
import os, sys
from Testing import ZopeTestCase
from testsupport import *

ZopeTestCase.installProduct('ZWiki')


class UITests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_STANDARD_TEMPLATES(self):
        STANDARD_TEMPLATES = ZWiki.UI.STANDARD_TEMPLATES
        # do all default templates have meta_types ? this has been fragile
        self.failIf(filter(lambda x:not hasattr(x,'meta_type'),STANDARD_TEMPLATES.values()))

import unittest
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UITests))
    return suite
