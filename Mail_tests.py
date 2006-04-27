from testsupport import *

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestsOfMailout))
    suite.addTest(unittest.makeSuite(TestsOfSubscription))
    return suite

class TestsOfMailout(unittest.TestCase):
    def setUp(self):
        self.p = mockPage()
        # mock up and record mail sending
        # XXX hacks MockZWikiPage class!
        self.p.mock_mailout_happened = 0
        def mock_sendMailToSubscribers(self, text, REQUEST, subjectSuffix='',
                                       subject='',message_id=None,in_reply_to=None,
                                       exclude_address=None):
            self.mock_mailout_happened = 1
            self.mock_mailout_text = text
            self.mock_mailout_REQUEST = REQUEST
            self.mock_mailout_subjectSuffix = subjectSuffix
            self.mock_mailout_subject = subject
        self.savemethod = self.p.__class__.sendMailToSubscribers
        self.p.__class__.sendMailToSubscribers = mock_sendMailToSubscribers

    def tearDown(self):
        self.p.__class__.sendMailToSubscribers = self.savemethod
        
    # see also testCommentFormatting
    def testCommentMailout(self):
        self.p.comment(text='comment',username='me',time='1999/12/31 GMT')
        self.assertEquals(self.p.mock_mailout_happened,1)

    #def testMailoutCommentWithOrWithoutSubjectField(self):
    # need to call the real sendMailToSubscribers
    #    self.p.comment(text='comment',username='me',time='now',
    #                   subject_heading='[test]')
    #    self.assertEquals(self.p.mock_mailout_happened,1)
    #    self.p.comment(text='comment',username='me',time='now')
    #    self.assertEquals(self.p.mock_mailout_happened,1)

    def testTextFormatter(self):
        # what's textformatter really doing ?
        from Products.ZWiki.TextFormatter import TextFormatter
        formatter = TextFormatter((
            {'width':78, 'fill':0, 'pad':0},
            ))
        self.assertEqual(formatter.compose(('',)),'')
        self.assertEqual(formatter.compose(('sometext',)),'sometext')
        self.assertEqual(formatter.compose(('sometext\n',)),'sometext')
        self.assertEqual(formatter.compose(('sometext\n\n',)),'sometext\n')
        self.assertEqual(formatter.compose(('sometext\n\n\n',)),'sometext\n\n')
        self.assertEqual(formatter.compose(('\nsometext',)),'\n sometext')
        self.assertEqual(formatter.compose(('\n\nsometext',)),'\n\nsometext')
        # chops a trailing newline and inserts a space after a single
        # leading newline

    # see also testZWikiPage.testCommentFormatting
    #def test_formatMailout(self):
    #    #fmt = self.p.formatMailout
    #    fmt = PageMailSupport().formatMailout
    #    # formatting nothing is ok
    #    self.assertEqual(fmt(' '),'')
    #    # fill paragraphs, strip leading and trailing newlines,
    #    # don't touch indented paragraphs or citations
    #    self.assertEqual(
    #        fmt('''
#
#long long long long long long long long long long long long long long long
#long long long line
#long long long long long long long long long long long long long long long
#long long long line
#
# long long long long long long long long long long long long long long long
#
#>long long long long long long long long long long long long long long long
#'''),
#            '''\
#long long long long long long long long long long long long long long
#long long long long line long long long long long long long long long
#long long long long long long long long long line
#
# long long long long long long long long long long long long long long long
#
#>long long long long long long long long long long long long long long
#>long
#''')


class TestsOfSubscription(unittest.TestCase):
    def test_isSubscriber(self):
        sl = mockPage()
        sl._setSubscribers(['a','b'])
        self.assert_(sl.isSubscriber('a'))
        self.assert_(not sl.isSubscriber('c'))
        self.assert_(not sl.isSubscriber(''))
        self.assert_(not sl.isSubscriber(' '))

    def test_subscribe(self):
        sl = mockPage()
        sl._setSubscribers(['spamandeggs'])
        self.assertEquals(sl.subscriberList(),['spamandeggs'])
        sl._resetSubscribers()
        self.assertEquals(sl.subscriberList(),[])
        self.assertEquals(sl.subscriberCount(),0)
        sl.subscribe('1@test.com')
        self.assertEquals(sl.subscriberList(),['1@test.com'])
        # check issue #161
        self.assertEquals(MockZWikiPage.subscriber_list,[]) 
        self.assertEquals(sl.subscriberCount(),1)
        self.assert_(sl.isSubscriber('1@test.com'))
        self.assert_(not sl.isSubscriber('2@test.com'))
        sl.subscribe('2@test.com')
        self.assertEquals(sl.subscriberList(),['1@test.com', '2@test.com'])
        self.assertEquals(sl.subscriberCount(),2)
        self.assert_(sl.isSubscriber('2@test.com'))
        sl.subscribe('1@test.com')
        self.assertEquals(sl.subscriberList(),['1@test.com', '2@test.com'])
        sl.unsubscribe('1@test.com')
        self.assertEquals(sl.subscriberList(),['2@test.com'])
        sl.unsubscribe('1@test.com')
        self.assertEquals(sl.subscriberList(),['2@test.com'])
        sl.unsubscribe('2@TesT.cOm')
        self.assertEquals(sl.subscriberList(),[])

    # XXX doesn't test subscription by CMF member id
    def test_allSubscriptionsFor(self):
        p = mockPage()
        p._resetSubscribers()
        p._resetSubscribers(parent=1)
        p.subscribe('a@a.a')
        p.subscribe('b@b.b')
        p.wikiSubscribe('b@b.b')
        self.assertEquals(p.allSubscriptionsFor('a@a.a'),['TestPage'])
        self.assertEquals(p.allSubscriptionsFor('b@b.b'),['whole_wiki', 'TestPage'])
        self.assertEquals(p.allSubscriptionsFor('c@c.c'),[])
        
    def test_otherSubscriptionsFor(self):
        thispage = mockPage(__name__='ThisPage')
        thispage.create('ThatPage')
        thatpage = thispage.aq_parent.ThatPage
        thispage.subscribe('me')
        thatpage.subscribe('me')
        thatpage.wikiSubscribe('me')
        self.assertEquals(thispage.otherPageSubscriptionsFor('me'),['ThatPage'])

    def test_unsubscribePreservesEditSubscriptions(self):
        """Test for #1255 bugfix"""
        p = mockPage()
        p.subscribe('a@a.a',edits=1)
        p.subscribe('b@b.b')
        p.unsubscribe('b@b.b')
        self.assert_('a@a.a' in p.subscriberList(edits=1))
        
