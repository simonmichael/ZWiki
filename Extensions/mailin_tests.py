from Products.ZWiki.testsupport import *
from Products.ZWiki.Extensions import mailin

THISPAGE    = 'TestPage'
TESTSENDER  = 'sender'
TESTTO      = 'recipient'
TESTDATE    = 'date'
TESTSUBJECT = 'subject'
TESTBODY    = 'mailin comment\n'
LONGSUBJECT = """\
a long long long long long long long long long long long long long subject"""

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

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


class Tests(unittest.TestCase):

    def setUp(self):
        self.p = mockPage(__name__=THISPAGE)
        self.p.folder().mailin_policy='open'
        
    def tearDown(self):
        del self.p

    # test the mailin delivery rules

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
        self.p.subscribe(TESTSENDER)
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

