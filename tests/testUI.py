import unittest
import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *

ZopeTestCase.installProduct('ZWiki')


class UITests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_DEFAULT_TEMPLATES(self):
        DEFAULT_TEMPLATES = ZWiki.UI.DEFAULT_TEMPLATES
        # do all default templates have meta_types ? this has been fragile
        self.failIf(filter(lambda x:not hasattr(x,'meta_type'),DEFAULT_TEMPLATES.values()))

if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(UITests))
        return suite
