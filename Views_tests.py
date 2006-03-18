from testsupport import *
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_STANDARD_TEMPLATES(self):
        STANDARD_TEMPLATES = ZWiki.Views.STANDARD_TEMPLATES
        # do all default templates have meta_types ? this has been fragile
        self.failIf(filter(lambda x:not hasattr(x,'meta_type'),STANDARD_TEMPLATES.values()))
