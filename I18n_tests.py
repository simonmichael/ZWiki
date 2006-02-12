# -*- coding: latin-1 -*-
#
# ISSUES
#
# 1. don't know how to make PTS return utf-8, so this file is latin-1
#
# 2. if PTS is on the filesystem, even without installProduct it does get
#    imported by support and will be active. But we'd like to test some
#    things without it. How do we prevent PTS installation ?
#
# 3. with PTS active, _() expects _getContext to find a request, normally
#    saved by ZPublisher. We patched it for (some) tests below, but the
#    problem remains for the other test modules, which also use _().  For
#    now we'll patch PTS for all (in support) and figure out later how to
#    let the below work.
#
# 4. should we skip translation tests when PTS is not available ?
#
# 5. these tests test PTS-based i18n, not generic i18n

import unittest
import os, sys
from Testing import ZopeTestCase
from testsupport import *

ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('PlacelessTranslationService')

from Products.ZWiki.I18nSupport import _
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
        # see ISSUES
        ## mock up stuff to get language control. The usual Pain.
        #from Products.PlacelessTranslationService.PlacelessTranslationService \
        #     import PlacelessTranslationService
        ## leave negotiation intact for later tests
        #try:
        #    save1 = PlacelessTranslationService._getContext
        #    save2 = PlacelessTranslationService.negotiate_language
        #    PlacelessTranslationService._getContext = \
        #        lambda self,context: MockRequest()
        #    PlacelessTranslationService.negotiate_language = \
        #        lambda self,context,domain: language
        #    translation = _(string)
        #finally:
        #    PlacelessTranslationService._getContext = save1
        #    PlacelessTranslationService.negotiate_language = save2
        translation = _(string)
        self.assertEqual(translation,expected)

    def test_python_i18n(self):
        self.assertTranslation('Page is locked','Page is locked')
        self.assertTranslation('Page is locked','La pagina è bloccata','it')

    #def test_pt_i18n(self):

    def test_dtml_translate_tag(self):
        self.p.allow_dtml = 1
        self.p.edit(
            text='<dtml-translate domain=zwiki>test</dtml-translate>')
        self.assert_(re.search('test', self.p(bare=1)))

    def test_addwikipageform(self):
        from DocumentTemplate.DT_Util import ParseError
        form = loadDtmlMethod('addwikipageform','skins/zmi')
        try: form(REQUEST=MockRequest())
        except NameError: self.fail()
        except KeyError: pass

    # see ISSUES

    def test_zmi_dtml_i18n(self):
        form = loadDtmlMethod('addwikipageform','skins/zmi')
        self.assert_(re.search('Add ZWiki Page',
                               form(REQUEST=MockRequest())))
        self.assert_(re.search('Add ZWiki Page IT',
                               form(REQUEST=MockRequest(language='it'))))
    
    def test_skin_dtml_i18n(self):
        # the searchwiki form includes searchwikidtml
        t = self.p.searchwiki(REQUEST=MockRequest())
        self.assert_(re.search('Enter a word',t))
        
        self.p.REQUEST = MockRequest(language='it')
        t = self.p.searchwiki(REQUEST=self.p.REQUEST)
        self.assert_(re.search(r'Enter a word IT',t))
    
    def test_page_dtml_i18n(self):
        self.p.allow_dtml = 1
        self.p.edit(
            text='<dtml-translate domain=zwiki>Enter a word</dtml-translate>')
        self.assert_(re.search('Enter a word', self.p(bare=1)))

        self.p.REQUEST = MockRequest(language='it')
        self.assert_(re.search('Enter a word IT', self.p(bare=1)))


import unittest
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    suite.level = 3 #XXX broken tests
    return suite
