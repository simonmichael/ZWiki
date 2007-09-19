from Products.ZWiki.testsupport import *
from Products.ZWiki.Extensions import mailin
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite


########################################################
# test data

THISPAGE    = 'TestPage'
TESTSENDER  = 'sender'
TESTTO      = 'recipient'
TESTDATE    = 'date'
TESTSUBJECT = 'subject'
TESTBODY    = 'mailin comment\n'
LONGSUBJECT = """\
a long long long long long long long long long long long long long subject"""

class TestMessage:
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

TESTMSG = str(TestMessage())

TESTDARCSMSG = """\
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
########################################################



class Tests(ZwikiTestCase):
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        self.wiki.mailin_policy='open'
        
    # from mailin.py:    
    #"decide which of the recipients is us, as follows:
    #
    #   1. if there's only one, it's that one
    #   2. the first one whose address matches the folder's mail_from property
    #   3. the first one whose address matches MAILINADDREXP
    #   4. the first one
    def testRecipientIdentification(self):
        m = mailin.MailIn(self.p.folder(),str(TestMessage(
            to='a'
            )))
        self.assertEqual(m.recipient(),('','a'))

        m = mailin.MailIn(self.p.folder(),str(TestMessage(
            to='a, b'
            )))
        self.assertEqual(m.recipient(),('','a'))

        self.p.folder().mail_from = 'b'
        m = mailin.MailIn(self.p.folder(),str(TestMessage(
            to='a, b, wiki@c.c'
            )))
        self.assertEqual(m.recipient(),('','b'))
        del self.p.folder().mail_from

        m = mailin.MailIn(self.p.folder(),str(TestMessage(
            to='a@a.a, mailin@b.b'
            )))
        self.assertEqual(m.recipient(),('','mailin@b.b'))

        m = mailin.MailIn(self.p.folder(),str(TestMessage(
            to='a@a.a, tracker@b.b'
            )))
        self.assertEqual(m.recipient(),('','tracker@b.b'))

        m = mailin.MailIn(self.p.folder(),str(TestMessage(
            to='a@a.a, bugs@b.b'
            )))
        self.assertEqual(m.recipient(),('','bugs@b.b'))

        m = mailin.MailIn(self.p.folder(),str(TestMessage(
            to='a@a.a, issues@b.b'
            )))
        self.assertEqual(m.recipient(),('','issues@b.b'))

    #def testDestinationFromFirstExistingPage(self):
    #    testmsg = str(TestMessage())
    #    self.p.create('APage')
    #    self.p.folder().default_page = 'NonExistentPage'
    #    m = mailin.MailIn(self.p.folder(),testmsg)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,THISPAGE)
    
    #def testDestinationFromRealNameWithRecognizedEmail(self):
    #    testmsg = str(TestMessage(to='wiki@b.c (SomePage)'))
    #    m = mailin.MailIn(self.p.folder(),testmsg,checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,'SomePage')
    
    #def testDestinationFromRealNameWithAnyEmail(self):
    #    testmsg = str(TestMessage(to='a@b.c (SomePage)'))
    #    m = mailin.MailIn(self.p.folder(),testmsg,checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,'SomePage')
    
    #def testDestinationFromRealNameWithSubject(self):
    #    testmsg = str(TestMessage(
    #        to='a@b.c (SomePage)',
    #        subject='[AnotherPage]',
    #        ))
    #    m = mailin.MailIn(self.p.folder(),testmsg,checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,'SomePage')
    
    def testDestinationWithNoNamedPage(self):
        m = mailin.MailIn(self.p.folder(), str(TestMessage(subject='test')))
        m.decideMailinAction()
        self.assertEqual(m.destpagename,'TestPage') 

    def testDestinationWithNoNamedPageAndDefaultMailinPageProperty(self):
        # should create a different page here but I have things to do!
        self.p.folder().default_mailin_page='TestPage'
        m = mailin.MailIn(self.p.folder(), str(TestMessage(subject='test')))
        m.decideMailinAction()
        self.assertEqual(m.destpagename,'TestPage') 

    def testDestinationWithNoNamedPageAndBlankDefaultMailinPageProperty(self):
        self.p.folder().default_mailin_page=''
        m = mailin.MailIn(self.p.folder(), str(TestMessage(subject='test')))
        m.decideMailinAction()
        self.assertEqual(m.destpagename,'') 

    #def testDestinationFromWikiNameInSubject(self):
    #    m = mailin.MailIn(self.p.folder(),
    #        str(TestMessage(subject='SomePage')))
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,None) 

    def testDestinationFromBracketedNameInSubject(self):
        m = mailin.MailIn(self.p.folder(),
            str(TestMessage(subject='[Some Page]')))
        m.decideMailinAction()
        self.assertEqual(m.destpagename,'Some Page')

    def testDestinationFromMultipleBracketedNamesInSubject(self):
        m = mailin.MailIn(
            self.p.folder(),
            str(TestMessage(subject='[Fwd:][LIST][Some Page]')))
        m.decideMailinAction()
        self.assertEqual(m.destpagename,'Some Page')
    
    def testDestinationFromLongSubject(self):
        m = mailin.MailIn(
            self.p.folder(),
            str(TestMessage(subject='['+' ....'*20+'Test Page'+' ....'*20+']')))
        m.decideMailinAction()
        self.assertEqual(m.destpage.pageName(),'TestPage')
    
    def testDestinationFromLongSubjectWithLineBreak(self):
        m = mailin.MailIn(
            self.p.folder(),
            str(TestMessage(subject='''\
Re: [IssueNo0547 mail (with long subject ?) may go to wrong page
 (test with long long long long long long subject)] property change''')))
        m.decideMailinAction()
        self.assertEqual(
            m.destpagename,
            'IssueNo0547 mail (with long subject ?) may go to wrong page (test with long long long long long long subject)')
    
    #def testDestinationWithBlankRealName(self):
    #    m = mailin.MailIn(self.p.folder(),str(TestMessage(
    #        to='wiki@b.c (   )',
    #        subject='SomePage',
    #        )),checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,None)

    #def testDestinationWithNoWordsInRealName(self):
    #    m = mailin.MailIn(self.p.folder(),str(TestMessage(
    #        to='wiki@b.c (...)',
    #        subject='SomePage',
    #        )),checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,None)

    #def testDestinationRealNameStripping(self):
    #    m = mailin.MailIn(self.p.folder(),str(TestMessage(
    #        to='wiki@b.c (  SomePage\t)',
    #        )),checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,'SomePage')

    #def testDestinationWithQuotesInRealName(self):
    #    m = mailin.MailIn(self.p.folder(),str(TestMessage(
    #        to="wiki@b.c ('SomePage')",
    #        )),checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,'SomePage')
    #    m = mailin.MailIn(self.p.folder(),str(TestMessage(
    #        to='wiki@b.c ("SomePage")',
    #        )),checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,'SomePage')

    #def testDestinationWithEmailInRealName(self):
    #    m = mailin.MailIn(self.p.folder(),str(TestMessage(
    #        to="wiki@b.c (wiki@b.c)",
    #        )),checkrecipient=1)
    #    m.decideMailinAction()
    #    self.assertEqual(m.destpagename,None)

    def testDestinationFromPageContext(self):
        m = mailin.MailIn(self.p,str(TestMessage(
            to='a@b.c (SomePage)',
            subject='[SomePage] SomePage',
            )))
        m.decideMailinAction()
        self.assertEqual(m.destpagename,THISPAGE)

    def testDestinationFromTrackerAddress(self):
        m = mailin.MailIn(self.p.folder(),str(TestMessage(
            to='bugs@b.c',
            )))
        m.decideMailinAction()
        self.assertEqual(m.trackerissue,1)

    def testSubscriberMailin(self):
        delattr(self.p.folder(),'mailin_policy')
        old = self.p.text()
        self.p.subscribe(TESTSENDER)
        mailin.mailin(self.p,TESTMSG)
        self.assertEqual(1, len(re.findall(TESTBODY,self.p.text())))
        
    def testNonSubscriberMailinFails(self):
        delattr(self.p.folder(),'mailin_policy')
        old = self.p.text()
        mailin.mailin(self.p,TESTMSG)
        self.assertEqual(old, self.p.read())
        
    def testNonSubscriberMailinWithOpenPosting(self):
        old = self.p.text()
        mailin.mailin(self.p,TESTMSG)
        self.assertEqual(1, len(re.findall(TESTBODY,self.p.text())))
        
    def testMailinMultipart(self):
        p = self.p
        p.subscribe(TESTSENDER)
        from email.MIMEText import MIMEText
        from email.MIMEMultipart import MIMEMultipart
        msg = MIMEMultipart()
        msg['From'] = TESTSENDER
        msg['To'] = TESTTO
        msg.attach(MIMEText('*bold*'))
        msg.attach(MIMEText('<b>bold</b>','html'))
        mailin.mailin(p, msg.as_string())
        self.assertEqual(1, p.commentCount())
        self.assertEqual(1, len(re.findall(r'\*bold\*', p.text())))

    def testMailinDarcsPatch(self):
        p = self.p
        p.subscribe(TESTSENDER)
        mailin.mailin(p,TESTDARCSMSG)
        self.assertEqual(1, p.commentCount())
        self.assert_('rename changes_rss to edits_rss' in p.text())
        # right now, should keep only first text part
        self.failIf('+    def edits_rss(self, num=3D10, REQUEST=3DNone):' in p.text())

    def testMailinTrackerIssue(self):
        self.p.upgradeFolderIssueProperties()
        self.assertEqual(0, self.p.issueCount())
        mailin.mailin(self.p.folder(),
                      str(TestMessage(to='bugs@somewhere')))
        self.assertEqual(1, self.p.issueCount())

    # this works.. need a functional test which sends through mail
    def testMailinTrackerIssueLongSubject(self):
        longsubjmsg = str(TestMessage(to='bugs@somewhere',subject=LONGSUBJECT))
        self.p.upgradeFolderIssueProperties()
        self.assertEqual(0, self.p.issueCount())
        mailin.mailin(self.p.folder(),longsubjmsg)
        self.assertEqual(1, self.p.issueCount())

    def testStripSignature(self):
        # signatures after -- should be stripped
        self.assertEqual(
            mailin.MailIn(self.p.folder(),str(TestMessage())).stripSignature(
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
        from mailin import MAX_SIGNATURE_STRIP_SIZE
        self.assertEqual(
            mailin.MailIn(self.p.folder(),str(TestMessage())).stripSignature(
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
            mailin.MailIn(self.p.folder(),str(TestMessage())).stripSignature(
            '''blah
---
blah'''),
            '''blah
---
blah''')
        self.assertEqual(
            mailin.MailIn(self.p.folder(),str(TestMessage())).stripSignature(
            '''blah
 --
blah'''),
            '''blah
 --
blah''')

