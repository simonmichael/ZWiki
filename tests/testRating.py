import unittest
import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *
#ZopeTestCase.installProduct('ZCatalog')
#ZopeTestCase.installProduct('ZWiki')
from Products.ZWiki.Rating import RatingSupport


class RatingTests(ZopeTestCase.ZopeTestCase):
    def setUp(self):
        self.rs = RatingSupport()

    def afterSetUp(self):
        pass #zwikiAfterSetUp(self)

    def test_rating(self):
        self.rs.resetRating()
        self.assert_(self.rs.rating() == 0)
        self.rs.setRating(2)
        self.assert_(self.rs.rating() == 2)

    def test_resetRating(self):
        self.rs.setRating(2)
        self.assert_(self.rs.rating() != 0)
        self.rs.resetRating()
        self.assert_(self.rs.rating() == 0)

    def test_setRating(self):
        self.assert_(self.rs.rating() != 2)
        self.rs.setRating(2)
        self.assert_(self.rs.rating() == 2)

    def test_rate(self):
        pass


if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(RatingTests))
        return suite
