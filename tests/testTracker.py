import unittest
import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *

ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('ZCatalog')


class Tests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_isIssue(self):
        def isIssue(name):
            self.p.create(page=name)
            return self.p.pageWithName(name).isIssue()
        self.failIf(isIssue('blah'))
        self.failIf(isIssue('IssueNo'))
        self.assert_(isIssue('IssueNo1'))
        self.assert_(isIssue('IssueNo1 blah'))
        self.assert_(isIssue('#1 blah'))
        self.failIf(isIssue('1'))

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

if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(Tests))
        return suite
