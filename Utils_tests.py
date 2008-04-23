# -*- coding: utf-8 -*-
from testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')
from Utils import TRACE, DEBUG, BLATHER, INFO, WARNING, ERROR

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):
    def test_checkSufficientId(self):
        p, r = self.page, self.request
        self.assert_(p.checkSufficientId(r))
        p.edits_need_username = 1
        self.failIf(p.checkSufficientId(r))
        p.edits_need_username = 0
        self.assert_(p.checkSufficientId(r))

    def test_safe_hasattr(self):
        from Utils import safe_hasattr
        p = self.page
        self.failIf(safe_hasattr(p,'muppets'))
        setattr(p, 'muppets', 'gonzo')
        self.assert_(safe_hasattr(p,'muppets'))

    def test_summary(self):
        p = self.page
        p.edit(text='É')
        self.assertEqual('É',p.summary())

    def test_BLATHER(self):
        BLATHER('E')                    # ascii
        BLATHER('É')                    # utf-8
        BLATHER(u'\xc9')                # unicode
        
