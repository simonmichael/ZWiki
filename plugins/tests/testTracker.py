import unittest
import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from Products.ZWiki.tests.support import *

ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('ZCatalog')


class TrackerSetupTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_setupTracker(self):
        p = self.p
        self.assertEqual(p.issueCount(),0)
        p.setupTracker()
        self.assertEqual(p.issueCount(),1)
        self.assert_(hasattr(p.folder(),'issue_severities'))

    def test_issueParentageWithSkinBasedTracker(self):
        f = self.p.folder()
        self.p.setupTracker()
        # without a tracker page, issues are parented under the creating page
        self.assertEqual(f.IssueNo0001FirstIssue.parents,[])
        f.IssueNo0001FirstIssue.createNextIssue('test')
        self.assertEqual(f.IssueNo0002Test.parents,[])
        
    def test_issueParentageWithPageBasedTracker(self):
        # with a tracker page, issues are parented under that
        f = self.p.folder()
        self.p.setupTracker(pages=1)
        self.assertEqual(f.IssueNo0001FirstIssue.parents,['IssueTracker'])
        f.IssueNo0001FirstIssue.createNextIssue('test')
        self.assertEqual(f.IssueNo0002Test.parents,['IssueTracker'])

    def test_upgradeIssueProperties(self):
        self.p.create('IssueNo0001')
        p = self.p.pageWithName('IssueNo0001')
        self.assert_(not hasattr(p,'severity'))
        p.upgradeIssueProperties()
        self.assert_(hasattr(p,'severity'))
        self.assertEqual(p.severity,'normal')


class TrackerTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)
        self.p.setupTracker()

    def test_isIssue(self):
        isIssue = self.p.isIssue
        self.assert_(not isIssue('blah'))
        self.assert_(not isIssue('1'))
        self.assert_(not isIssue('IssueNo'))
        self.assert_(    isIssue('IssueNo1'))
        self.assert_(not isIssue('#1'))
        self.p.folder().short_issue_names = 1
        self.assert_(    isIssue('IssueNo1'))
        self.assert_(    isIssue('#1'))
        
    def test_issueNumberFrom(self):
        issueNumberFrom = self.p.issueNumberFrom
        self.failIf(issueNumberFrom('#1 blah'))
        self.assertEqual(issueNumberFrom('IssueNo1'),1)
        self.assertEqual(issueNumberFrom('IssueNo1 blah'),1)
        self.p.folder().short_issue_names = 1
        self.assertEqual(issueNumberFrom('IssueNo1'),1)
        self.assertEqual(issueNumberFrom('#2 blah'),2)

    def test_createNextIssue(self):
        self.p.createNextIssue('b')
        self.assert_(self.p.pageWithName('IssueNo0002 b'))
        self.p.folder().short_issue_names = 1
        self.p.createNextIssue('c')
        self.assert_(self.p.pageWithName('#3 c'))
        self.assertEqual(self.p.issueCount(),3)
        

if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TrackerSetupTests))
        suite.addTest(unittest.makeSuite(TrackerTests))
        return suite
