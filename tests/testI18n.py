# -*- coding: latin-1 -*-
# don't know how to make PTS return utf-8 translations 

import unittest
import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *

ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('PlacelessTranslationService')

from Products.ZWiki.I18nSupport import DTMLFile, _ #will it get i18nextracted ?
from Products.ZWiki.UI import loadDtmlMethod


class Tests(ZopeTestCase.ZopeTestCase):
    """
    Unit tests for Zwiki i18n, aka "blood, sweat and tears".
    
    Tips for MockZWikiPage, MockRequest, PTS etc.:
    - use a fresh request to avoid PTS language caching
    - the REQUEST argument is often required
    - set a page's REQUEST attribute as well
    - bare=1 can also help get pages rendering

    """
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def assertTranslation(self,string,expected,language='en'):
        # mock up stuff to get language control. The usual Pain.
        from Products.PlacelessTranslationService.PlacelessTranslationService \
             import PlacelessTranslationService
        # leave negotiation intact for later tests
        try:
            save1 = PlacelessTranslationService._getContext
            save2 = PlacelessTranslationService.negotiate_language
            PlacelessTranslationService._getContext = \
                lambda self,context: MockRequest()
            PlacelessTranslationService.negotiate_language = \
                lambda self,context,domain: language
            translation = str(_(string))
        finally:
            PlacelessTranslationService._getContext = save1
            PlacelessTranslationService.negotiate_language = save2
        self.assertEqual(translation,expected)

    def test_python_i18n(self):
        self.assertTranslation('Page is locked','Page is locked')
        self.assertTranslation('Page is locked','La pagina è bloccata','it')

    #def test_pt_i18n(self):

    #def test_dtml_gettext_tag(self):
    #    form = loadDtmlMethod('zwikiWebAdd','dtml')
    #    try: form(REQUEST=MockRequest())
    #    except NameError: self.fail()
    #    except (KeyError,ParseError): pass

    def test_dtml_translate_tag(self):
        from DocumentTemplate.DT_Util import ParseError
        form = loadDtmlMethod('zwikiPageAdd','dtml')
        try: form(REQUEST=MockRequest())
        except NameError: self.fail()
        except KeyError: pass

    #def test_zmi_dtml_messages_extracted(self):

    def test_zmi_dtml_i18n(self):
        form = loadDtmlMethod('zwikiPageAdd','dtml')
        self.assert_(re.search('Add ZWiki Page',
                               form(REQUEST=MockRequest())))
        self.assert_(re.search('Add ZWiki Page IT',
                               form(REQUEST=MockRequest(language='it'))))
    
    #def test_skin_dtml_messages_extracted(self):

    def test_skin_dtml_i18n(self):
        # the searchwiki form includes searchwikidtml
        t = self.p.searchwiki(REQUEST=MockRequest())
        self.assert_(re.search('Enter a word',t))
        
        self.p.REQUEST = MockRequest(language='it')
        t = self.p.searchwiki(REQUEST=self.p.REQUEST)
        self.assert_(re.search(r'Enter a word IT',t))
    
    #def test_page_dtml_messages_extracted(self):

    def test_page_dtml_i18n(self):
        self.p.allow_dtml = 1
        self.p.edit(
            text='<dtml-translate domain=zwiki>Enter a word</dtml-translate>')
        self.assert_(re.search('Enter a word', self.p(bare=1)))

        self.p.REQUEST = MockRequest(language='it')
        self.assert_(re.search('Enter a word IT', self.p(bare=1)))


if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(Tests))
        return suite
