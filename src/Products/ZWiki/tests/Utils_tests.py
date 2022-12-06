# -*- coding: utf-8 -*-
from testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')
from Products.ZWiki.Utils import TRACE, DEBUG, BLATHER, INFO, WARNING, ERROR

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
        from Products.ZWiki.Utils import safe_hasattr
        p = self.page
        self.failIf(safe_hasattr(p,'muppets'))
        setattr(p, 'muppets', 'gonzo')
        self.assert_(safe_hasattr(p,'muppets'))

    def test_excerptAt(self):
        self.page.edit(text='This is a test of the<br />\n excerptAt method,')
        self.assertEquals(self.page.excerptAt('excerptat',size=10,highlight=0),
                          '\n excerptAt ')
        #self.assertEquals(self.page.excerptAt('this*',size=21,highlight=1),
        #                  '<span class="hit">This</span> is a tes')
        #self.assertEquals(self.page.excerptAt('br',size=4),
        #                  'e&lt;<span class="hit">br</span>&gt;\n')
        # XXX temp
        self.assertEquals(self.page.excerptAt('this*',size=21,highlight=1),
                          '<span class="hit" style="background-color:yellow;font-weight:bold;">This</span> is a tes')
        self.assertEquals(self.page.excerptAt('br',size=4),
                          'e&lt;<span class="hit" style="background-color:yellow;font-weight:bold;">br</span> /')
        self.assertEquals(self.page.excerptAt('<br />',size=4,highlight=0),
                          '&lt;br /&gt;')
        self.assertEquals(self.page.excerptAt('nomatch'), 'This is a test of the&lt;br /&gt;\n excerptAt method,')
        self.assertEquals(self.page.excerptAt(''), 'This is a test of the&lt;br /&gt;\n excerptAt method,')

    def test_summary(self):
        p = self.page
        p.edit(text=u'É')
        self.assertEqual(u'É',p.summary())

    def test_BLATHER(self):
        BLATHER('E')                    # ascii
        BLATHER('É')                    # utf-8
        BLATHER(u'\xc9')                # unicode

