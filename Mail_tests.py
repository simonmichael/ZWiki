from testsupport import *
from Mail import MailIn, stripBottomQuoted, stripSignature
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SubscriptionTests))
    suite.addTest(unittest.makeSuite(MailoutTests))
    suite.addTest(unittest.makeSuite(MailinTests))
    return suite

class SubscriptionTests(ZwikiTestCase):
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
        self.assertEquals(sl.pageSubscriberCount(),0)
        self.assertEquals(sl.wikiSubscriberCount(),0)
        sl.subscribe('1@test.com')
        self.assertEquals(sl.subscriberList(),['1@test.com'])
        # check issue #161
        self.assertEquals(MockZWikiPage.subscriber_list,[]) 
        self.assertEquals(sl.subscriberCount(),1)
        self.assertEquals(sl.pageSubscriberCount(),1)
        self.assertEquals(sl.wikiSubscriberCount(),0)
        self.assert_(sl.isSubscriber('1@test.com'))
        self.assert_(not sl.isSubscriber('2@test.com'))
        sl.subscribe('2@test.com')
        self.assertEquals(sl.subscriberList(),['1@test.com', '2@test.com'])
        self.assertEquals(sl.subscriberCount(),2)
        self.assertEquals(sl.pageSubscriberCount(),2)
        self.assertEquals(sl.wikiSubscriberCount(),0)
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
        
    def test_TextFormatter(self):
        # what's textformatter really doing ?
        from TextFormatter import TextFormatter
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


class MailoutTests(ZwikiTestCase):
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        # hacky mock mail sending
        self.p.mock_mailout_happened = 0
        def mock_sendMailToSubscribers(self, text, REQUEST, subjectSuffix='',
                                       subject='',message_id=None,in_reply_to=None,
                                       exclude_address=None):
            self.mock_mailout_happened = 1
            self.mock_mailout_text = text
            self.mock_mailout_REQUEST = REQUEST
            self.mock_mailout_subjectSuffix = subjectSuffix
            self.mock_mailout_subject = subject
        self.realmethod = self.p.__class__.sendMailToSubscribers
        self.p.__class__.sendMailToSubscribers = mock_sendMailToSubscribers

    def beforeTearDown(self):
        self.p.__class__.sendMailToSubscribers = self.realmethod

    def test_commentMailout(self):
        self.p.comment(text='comment',username='me',time='1999/12/31 GMT')
        self.assertEquals(self.p.mock_mailout_happened,1)

    def test_mailoutCommentWithOrWithoutSubjectField(self):
        self.p.comment(text='comment',username='me',subject_heading='[test]')
        self.assertEquals(self.p.mock_mailout_happened,1)
        self.p.mock_mailout_happened = 0
        self.p.comment(text='comment',username='me')
        self.assertEquals(self.p.mock_mailout_happened,1)


THISPAGE    = 'TestPage'
TESTSENDER  = 'sender'
TESTTO      = 'recipient'
TESTDATE    = 'date'
TESTSUBJECT = 'subject'
TESTBODY    = 'mailin comment\n'
LONGSUBJECT = """\
a long long long long long long long long long long long long long subject"""

class TestMessage:
    """Builds an email message that we can adjust easily."""
    def __init__(self,sender=TESTSENDER,to=TESTTO,cc='',bcc='',
                 date=TESTDATE,subject=TESTSUBJECT,body=TESTBODY):
        self.sender,self.to,self.cc,self.bcc,self.date,self.subject,self.body=\
          (sender,to,cc,bcc,date,subject,body)

    def __call__(self):
        s = """\
From: %s
To: %s
""" % (self.sender, self.to)
        if self.cc:
            s = s + "Cc: %s\n" + self.cc
        if self.bcc:
            s = s + "Bcc: %s\n" + self.bcc
        s = s + """\
Date: %s
Subject: %s

%s
""" % (self.date, self.subject, self.body)
        return s

    __str__ = __call__

TESTMSG = """\
From: sender
To: recipient
Date: date
Subject: subject

mailin comment


"""

BOTTOMQUOTEDMSG = """\
From: sender
To: recipient
Date: date
Subject: subject

mailin comment

-----Original Message-----
From: someone
Sent: ...
To: ...
Subject: blah blah blah

blah BLAH
"""

BOTTOMQUOTEDMSG2 = """\
From: sender
To: recipient
Date: date
Subject: subject

mailin comment

On Jan 14, 2008 10:28 AM, Someone <someone@here> wrote:
>
> BLAH BLAH
"""

DARCSMSG = """\
To: a@b.com
From: a@b.com
Subject: darcs patch: rename changes_rss to edits_rss
X-Mail-Originator: Darcs Version Control System
X-Darcs-Version: 1.0.8 (stable branch)
DarcsURL: zwiki.org:/repos/ZWiki
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="=_"
Date: Tue, 18 Sep 2007 08:27:57 -0700

--=_
Content-Type: text/plain
Content-Transfer-Encoding: quoted-printable

Tue Sep 18 08:21:35 PDT 2007  simon@joyful.com
  * rename changes_rss to edits_rss (with a backwards compatibility alias) =
and
  update the docstring. Also, test forwarding to the PatchDiscussion page.

--=_
Content-Type: text/x-darcs-patch; name="rename-changes_rss-to-edits_rss-_with-a-backwards-compatibility-alias_-and.dpatch"
Content-Transfer-Encoding: quoted-printable
Content-Description: A darcs patch for your repository!


New patches:

[rename changes_rss to edits_rss (with a backwards compatibility alias) and
simon@joyful.com**20070918152135
 update the docstring. Also, test forwarding to the PatchDiscussion page.
] {
hunk ./RSS.py 96
-    security.declareProtected(Permissions.View, 'changes_rss')
-    def changes_rss(self, num=3D10, REQUEST=3DNone):
-        \"\"\"
-        Provide an RSS feed showing this wiki's recently edited pages.
-
-        This is not the same as all recent edits.
+    security.declareProtected(Permissions.View, 'edits_rss')
+    def edits_rss(self, num=3D10, REQUEST=3DNone):
+        \"\"\"Provide an RSS feed listing this wiki's N most recently edited
+        pages. May be useful for monitoring, as a (less detailed)
+        alternative to an all edits mail subscription.
hunk ./RSS.py 156
+    # backwards compatibility
+    changes_rss =3D edits_rss
}

Context:

[1272 - create PageBrain only for Zwiki Pages.
betabug.darcs@betabug.ch**20070917193709
 Since we are now ensuring that there is always a catalog in a Zwiki,
 the method metadataFor() shouldn't be needed any more. But I'm still
 adding this patch (credits and thanks to koegler), in case some code
 hits on it in the time between an upgrade and running the /upgradeAll
 method.
] =

[TAG release-0-60-0
simon@joyful.com**20070915222130] =

Patch bundle hash:
a639bc8070d08220e8db873a991da5f2955e58db

--=_--

.

"""

class MailinTests(ZwikiTestCase):
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        self.wiki.mailin_policy='open'
        
    def test_stripSignature(self):
        # signatures after -- should be stripped
        self.assertEqual(
            stripSignature(
            '''
blah blah

--
my signature
blah blah blah
'''),
            '''
blah blah

''')
        # unless they are too large
        from Mail import MAX_SIGNATURE_STRIP_SIZE
        self.assertEqual(
            stripSignature(
            '''
blah blah

--
''' + 'x'*(MAX_SIGNATURE_STRIP_SIZE+1)),
            '''
blah blah

--
''' + 'x'*(MAX_SIGNATURE_STRIP_SIZE+1))
        # leave other things alone
        self.assertEqual(
            stripSignature(
            '''blah
---
blah'''),
            '''blah
---
blah''')
        self.assertEqual(
            stripSignature(
            '''blah
 --
blah'''),
            '''blah
 --
blah''')

    def test_stripBottomQuoted(self):
        def linecount(s): return len(s.split('\n'))
        self.assertEqual(linecount(stripBottomQuoted(BOTTOMQUOTEDMSG)),8) # re bug, should be 7
        #self.assertEqual(linecount(stripBottomQuoted(BOTTOMQUOTEDMSG2)),8) # XXX not implemented

    def test_recipientIdentification(self):
        # from Mail.py:
        # If the message has multiple recipients, decide which one refers to us
        # as follows:
        # - the first recipient matching the folder's mail_from property,
        # - or the first one looking like a typical zwiki mailin alias (.*MAILINADDREXP),
        # - or the first one.
        m = MailIn(self.p,str(TestMessage(to='a')))
        self.assertEqual(m.recipient(),('','a'))

        m = MailIn(self.p,str(TestMessage(to='a, b')))
        self.assertEqual(m.recipient(),('','a'))

        self.p.folder().mail_from = 'b'
        m = MailIn(self.p,str(TestMessage(to='a, b, wiki@c.c')))
        self.assertEqual(m.recipient(),('','b'))
        del self.p.folder().mail_from

        m = MailIn(self.p,str(TestMessage(to='a@a.a, mailin@b.b')))
        self.assertEqual(m.recipient(),('','mailin@b.b'))

        m = MailIn(self.p,str(TestMessage(to='a@a.a, tracker@b.b')))
        self.assertEqual(m.recipient(),('','tracker@b.b'))

        m = MailIn(self.p,str(TestMessage(to='a@a.a, bugs@b.b')))
        self.assertEqual(m.recipient(),('','bugs@b.b'))

        m = MailIn(self.p,str(TestMessage(to='a@a.a, issues@b.b')))
        self.assertEqual(m.recipient(),('','issues@b.b'))

    def test_destinationWithNoNamedPage(self):
        m = MailIn(self.p, str(TestMessage(subject='test')))
        self.assertEqual(m.decideMailinAction(),('COMMENT','TestPage')) 

    def test_destinationWithNoNamedPageAndDefaultMailinPageProperty(self):
        self.p.folder().default_mailin_page='TestPage'
        m = MailIn(self.p, str(TestMessage(subject='test')))
        self.assertEqual(m.decideMailinAction(),('COMMENT','TestPage')) 

    def test_destinationWithNoNamedPageAndBlankDefaultMailinPageProperty(self):
        self.p.folder().default_mailin_page=''
        m = MailIn(self.p, str(TestMessage(subject='test')))
        action, info = m.decideMailinAction()
        self.assertEqual(action,'ERROR')

    def test_destinationFromBracketedNameInSubject(self):
        m = MailIn(self.p, str(TestMessage(subject='[Some Page]')))
        self.assertEqual(m.decideMailinAction(),('CREATE','Some Page'))

    def test_destinationFromMultipleBracketedNamesInSubject(self):
        m = MailIn(self.p, str(TestMessage(subject='[Fwd:][LIST][Some Page]')))
        self.assertEqual(m.decideMailinAction(),('CREATE','Some Page')) 
    
    def test_destinationFromLongSubject(self):
        m = MailIn(self.p,
                   str(TestMessage(subject='['+' ....'*20+'Test Page'+' ....'*20+']')))
        self.assertEqual(m.decideMailinAction(),('COMMENT','TestPage')) 
    
    def test_destinationFromLongSubjectWithLineBreak(self):
        m = MailIn(self.p,
                   str(TestMessage(subject='''\
Re: [IssueNo0547 mail (with long subject ?) may go to wrong page
 (test with long long long long long long subject)] property change''')))
        self.assertEqual(m.decideMailinAction(),
                         ('CREATE',
                          'IssueNo0547 mail (with long subject ?) may go to wrong page (test with long long long long long long subject)'))
    
    def test_destinationFromTrackerAddress(self):
        m = MailIn(self.p, str(TestMessage(to='bugs@b.c',)))
        action, info = m.decideMailinAction()
        self.assertEqual(action,'ISSUE')

    def test_subscriberMailin(self):
        delattr(self.p.folder(),'mailin_policy')
        old = self.p.text()
        self.p.subscribe(TESTSENDER)
        self.p.mailin(TESTMSG)
        self.assertEqual(1, len(re.findall(TESTBODY,self.p.text())))
        
    def test_nonSubscriberMailinFails(self):
        delattr(self.p.folder(),'mailin_policy')
        old = self.p.text()
        self.p.mailin(TESTMSG)
        self.assertEqual(old, self.p.read())
        
    def test_nonSubscriberMailinWithOpenPosting(self):
        old = self.p.text()
        self.p.mailin(TESTMSG)
        self.assertEqual(1, len(re.findall(TESTBODY,self.p.text())))
        
    def test_mailinTrackerIssue(self):
        self.p.setupTracker()
        self.assertEqual(1, self.p.issueCount())
        self.p.mailin(str(TestMessage(to='bugs@somewhere')))
        self.assertEqual(2, self.p.issueCount())

    def test_mailinTrackerIssueLongSubject(self):
        longsubjmsg = str(TestMessage(to='bugs@somewhere',subject=LONGSUBJECT))
        self.p.setupTracker()
        self.assertEqual(1, self.p.issueCount())
        self.p.mailin(longsubjmsg)
        self.assertEqual(2, self.p.issueCount())

    def test_mailinMultipart(self):
        p = self.p
        p.subscribe(TESTSENDER)
        from email.MIMEText import MIMEText
        from email.MIMEMultipart import MIMEMultipart
        msg = MIMEMultipart()
        msg['From'] = TESTSENDER
        msg['To'] = TESTTO
        msg.attach(MIMEText('*bold*'))
        msg.attach(MIMEText('<b>bold</b>','html'))
        p.mailin(msg.as_string())
        self.assertEqual(1, p.commentCount())
        self.assertEqual(1, len(re.findall(r'\*bold\*', p.text())))

    def test_mailinDarcsPatch(self):
        p = self.p
        p.subscribe(TESTSENDER)
        p.mailin(DARCSMSG)
        self.assertEqual(1, p.commentCount())
        self.assert_('rename changes_rss to edits_rss' in p.text())

