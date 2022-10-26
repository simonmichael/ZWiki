from Products.ZWiki.tests.testsupport import *
ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZCTextIndex')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestsOfTrackerSetup))
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class TestsOfTrackerSetup(ZwikiTestCase):

    def test_setupTracker(self):
        p = self.p
        self.assertEqual(p.issueCount(),0)
        p.setupTracker()
        self.assertEqual(p.issueCount(),1)
        self.assert_(safe_hasattr(p.folder(),'issue_severities'))

    def test_issueParentageWithSkinBasedTracker(self):
        f = self.p.folder()
        self.p.setupTracker()
        # without a tracker page, issues are parented under the creating page
        self.assertEqual(f['1FirstIssue'].parents,[])
        f['1FirstIssue'].createNextIssue('test')
        self.assertEqual(f['2Test'].parents,[])

    def test_issueParentageWithPageBasedTracker(self):
        # with a tracker page, issues are parented under that
        f = self.p.folder()
        self.p.setupTracker(pages=1)
        self.assertEqual(f['1FirstIssue'].parents,['IssueTracker'])
        f['1FirstIssue'].createNextIssue('test')
        self.assertEqual(f['2Test'].parents,['IssueTracker'])

    def test_upgradeIssueProperties(self):
        self.p.create('IssueNo0001')
        p = self.p.pageWithName('IssueNo0001')
        self.assert_(not safe_hasattr(p,'severity'))
        p.upgradeIssueProperties()
        self.assert_(safe_hasattr(p,'severity'))
        self.assertEqual(p.severity,'normal')


class Tests(ZwikiTestCase):
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        self.p.setupTracker()

    def test_isIssue(self):
        isIssue = self.p.isIssue
        self.assert_(not isIssue('blah'))
        self.assert_(not isIssue('1'))
        self.assert_(not isIssue('IssueNo'))
        self.assert_(    isIssue('IssueNo1'))
        self.assert_(    isIssue('#1'))

    def test_issueNumberFrom(self):
        issueNumberFrom = self.p.issueNumberFrom
        self.assertEqual(issueNumberFrom('IssueNo1'),1)
        self.assertEqual(issueNumberFrom('IssueNo1 blah'),1)
        self.assertEqual(issueNumberFrom('#2'),2)
        self.assertEqual(issueNumberFrom('#2 blah'),2)

    def test_createNextIssue(self):
        self.p.createNextIssue('b')
        self.assert_(self.p.pageWithName('#2 b'))
        self.assertEqual(self.p.issueCount(),2)

    def test_nextIssueNumber(self):
        self.assertEqual(self.p.nextIssueNumber(),2)
        self.p.createNextIssue('b')
        self.assertEqual(self.p.nextIssueNumber(),3)

    def test_issuePageWithNumber(self):
        self.assert_(self.p.issuePageWithNumber(1))
        self.assert_(not self.p.issuePageWithNumber(2))
        self.p.createIssue('#456 test')
        self.assert_(not self.p.issuePageWithNumber(4))
        self.assert_(not self.p.issuePageWithNumber(4567))
        self.assert_(self.p.issuePageWithNumber(456))

    def test_issue_links(self):
        # test the full two-step linking procedure
        link = lambda t: self.p.renderMarkedLinksIn(self.p.markLinksIn(t))
        # #1 links to issue 1
        self.assertEquals(link('#1')[-6:],  '#1</a>')
        # [#1] doesn't (should ?)
        self.assertEquals(link('[#1]')[-6:],  '>?</a>')
        # an issue name part doesn't matter
        self.p.createIssue('#987 test')
        self.assertEquals(link('#987')[-8:],'#987</a>')
        # all digits are required
        self.failIf(link('#9')[-6:].endswith('</a>'))

    def test_fuzzy_urls_for_issues(self):
        p = self.page
        issue2 = p.pageWithName(p.create('#2 x'))
        issue20 = p.pageWithName(p.create('#20 x'))
        issue200 = p.pageWithName(p.create('#200 x'))
        self.assertEqual(issue2, p.pageWithFuzzyName('2', allow_partial=1))
        issue2.delete()
        self.assertEqual(issue20, p.pageWithFuzzyName('2', allow_partial=1))

