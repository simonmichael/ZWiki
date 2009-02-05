# -*- coding: utf-8 -*-
from Products.ZWiki.tests.testsupport import *
from Products.ZWiki.pagetypes.stx import PageTypeStx
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        self.p.edit(type='stx')

    def test_edit(self):
        self.p.edit(text='! PageOne PageTwo\n')
        self.assertEquals(self.p.render(bare=1),'<p> PageOne PageTwo</p>\n<p>\n</p>\n')

    def test_non_ascii_edit(self):
        self.p.edit(text='É')
        self.assertEquals(u'<p>É</p>\n<p>\n</p>\n', self.p.render(bare=1))
                          
    #def test_stxToHtml(self):
    #    p = self.page
    #    # handle a STX table or other error gracefully
    #    self.assertEquals(p.stxToHtml('+-+-+\n| | |\n+-+-+'),
    #                      '')

    def test_mailto_with_dot_1115(self):
        self.assertEquals(
            u'<p><a href="mailto:&#97;&#46;&#98;&#64;&#99;&#46;&#99;&#111;&#109;">&#97;&#46;&#98;&#64;&#99;&#46;&#99;&#111;&#109;</a></p>\n<p>\n</p>\n',
            self.p.renderText('mailto:a.b@c.com','stx'))
