# -*- coding: utf-8 -*-

import unittest
import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *

ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('PlacelessTranslationService')

# patch PTS for testing
from Products.PlacelessTranslationService.PlacelessTranslationService import \
     PlacelessTranslationService
PlacelessTranslationService._getContext = lambda self,context: MockRequest()
def setLanguage(language):
    PlacelessTranslationService.negotiate_language = \
      lambda self,context,domain: language
setLanguage('en')

from Products.ZWiki.I18nSupport import _


class Tests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def assertTranslation(self,string,translated,language='en'):
        setLanguage(language)
        self.assertEqual(str(_(string)),translated)

    def test_python_i18n(self):
        self.assertTranslation('Page is locked','Page is locked')
        self.assertTranslation('Page is locked','La pagina è bloccata','it')
        self.assertTranslation('Page is locked',
                               'La page est v&eacute;rouill&eacute;e','fr')
        self.assertTranslation('Page is locked',
                               'A página está bloqueada','pt-br')
        self.assertTranslation(
            'Page is locked',
            '頁面被鎖',
            'zh-tw')

    #def test_PT_i18n(self):

    #def test_DTML_i18n_in_ZMI(self):
    
    #def test_DTML_i18n_in_skins(self):
    
    #def test_DTML_i18n_in_pages(self):


if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(Tests))
        return suite
