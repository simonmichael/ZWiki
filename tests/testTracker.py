import unittest
import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *

ZopeTestCase.installProduct('ZWiki')


class Tests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_upgradeIssueProperties(self):
        self.p.create('IssueNo0001')
        p = self.p.pageWithName('IssueNo0001')
        self.assert_(not hasattr(p,'severity'))
        p.upgradeIssueProperties()
        self.assert_(hasattr(p,'severity'))
        self.assertEqual(p.severity,'normal')

    def test_setupTracker(self):
        p = self.p
        self.assertEqual(p.issueCount(),0)
        p.setupTracker()
        self.assertEqual(p.issueCount(),1)
        self.assert_(hasattr(p.folder(),'issue_severities'))

    def test_issueParentageWithSkinBasedTracker(self):
        self.p.setupTracker()
        f = self.p.folder()
        self.assertEqual(f.IssueNo0001FirstIssue.parents,
                         ['TestPage'])
        f.IssueNo0001FirstIssue.createNextIssue('')
        self.assertEqual(f.IssueNo0002.parents,
                         ['IssueNo0001 first issue'])
        
    def test_issueParentageWithPageBasedTracker(self):
        self.p.setupTracker()
        f = self.p.folder()
        self.p.setupTracker(pages=1)

if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(Tests))
        return suite
