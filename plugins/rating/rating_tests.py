import unittest
import os, sys
from Testing import ZopeTestCase
from Products.ZWiki.testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')


class RatingTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)
        self.p.REQUEST.REMOTE_ADDR = '1'
        self.p.resetVotes()

    def test_rating(self):
        p = self.p
        self.assert_(p.rating() == 1)
        p.vote(2)
        self.assert_(p.rating() == 2)
        self.p.REQUEST.REMOTE_ADDR = 'another'
        p.vote(0)
        self.assert_(p.rating() == 1)

    def test_vote(self): # and voteCount
        p = self.p
        self.assert_(p.voteCount() == 0)
        p.vote(1)
        self.assert_(p.voteCount() == 1)
        p.vote(1)
        self.assert_(p.voteCount() == 1)
        self.p.REQUEST.REMOTE_ADDR = 'another'
        p.vote(1)
        self.assert_(p.voteCount() == 2)


import unittest
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RatingTests))
    return suite
