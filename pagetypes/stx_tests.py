import os, sys
from Testing import ZopeTestCase
from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

class Tests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_ZwikiStxPageType(self):
        self.p.edit(text='! PageOne PageTwo\n',type='stx')
        self.assertEquals(self.p.render(bare=1),
                          '<p> PageOne PageTwo</p>\n<p>\n</p>\n')


import unittest
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite
