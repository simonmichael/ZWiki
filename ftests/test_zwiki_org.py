# functional tests for zwiki.org

import os, sys, re, string
import unittest
from curltest import TestBase

SITE='http://zwiki.org'

class Tests(TestBase):

    def test_can_view_front_page(self):
        self.assertPageContains(SITE,'Welcome to Zwiki!')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

if __name__ == '__main__': 
    unittest.TextTestRunner().run(test_suite())
