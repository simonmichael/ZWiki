# unit tests for the mailin external method

from support import *
import sys
Extensions_dir = os.path.join(os.path.dirname(ZWiki.__file__),'Extensions')
sys.path.append(Extensions_dir)
import mailin

THISPAGE    = 'TestPage'
assert(THISPAGE != mailin.DEFAULTPAGE) # avoid confusion

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


class MailinTests(unittest.TestCase):

    def setUp(self):
        self.p = MockZWikiPage(__name__=THISPAGE)
        # mock up the IssueTracker page, capture the REQUEST
        # hacks Folder class
        def IssueTracker(self,REQUEST=None):
            self.issuetracker_request = REQUEST
        self.p.aq_parent.__class__.IssueTracker = IssueTracker
        
    def tearDown(self):
        del self.p.aq_parent.__class__.IssueTracker
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
        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='a'
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.recipient,('','a'))

        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='a, b'
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.recipient,('','a'))

        self.p.folder().mail_from = 'b'
        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='a, b, wiki@c.c'
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.recipient,('','b'))
        del self.p.folder().mail_from

        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='a@a.a, mailin@b.b'
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.recipient,('','mailin@b.b'))

        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='a@a.a, tracker@b.b'
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.recipient,('','tracker@b.b'))

        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='a@a.a, bugs@b.b'
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.recipient,('','bugs@b.b'))

        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='a@a.a, issues@b.b'
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.recipient,('','issues@b.b'))

    def testDestinationFromHardCodedDefaultPage(self):
        testmsg = str(TestMessage())
        self.p.create('APage')
        self.p.create(mailin.DEFAULTPAGE)
        m = mailin.MailIn(self.p.aq_parent,testmsg,subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,mailin.DEFAULTPAGE)
    
    def testDestinationFromDefaultPageProperty(self):
        testmsg = str(TestMessage())
        self.p.create('APage')
        self.p.create('BPage')
        self.p.aq_parent.default_page = 'BPage'
        m = mailin.MailIn(self.p.aq_parent,testmsg,subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'BPage')
    
    def testDestinationFromFirstExistingPage(self):
        testmsg = str(TestMessage())
        self.p.create('APage')
        self.p.aq_parent.default_page = 'NonExistentPage'
        m = mailin.MailIn(self.p.aq_parent,testmsg,subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,THISPAGE)
    
    def testDestinationFromRealNameWithRecognizedEmail(self):
        testmsg = str(TestMessage(to='wiki@b.c (SomePage)'))
        m = mailin.MailIn(self.p.aq_parent,testmsg,subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'SomePage')
    
    def testDestinationFromRealNameWithAnyEmail(self):
        testmsg = str(TestMessage(to='a@b.c (SomePage)'))
        m = mailin.MailIn(self.p.aq_parent,testmsg,subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'SomePage')
    
    def testDestinationFromRealNameWithSubject(self):
        testmsg = str(TestMessage(
            to='a@b.c (SomePage)',
            subject='[AnotherPage]',
            ))
        m = mailin.MailIn(self.p.aq_parent,testmsg,subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'SomePage')
    
    def testDestinationFromWikiNameInSubject(self):
        # we don't do this any more
        m = mailin.MailIn(self.p.aq_parent,
            str(TestMessage(subject='SomePage')),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,THISPAGE) 

    def testDestinationFromBracketedNameInSubject(self):
        m = mailin.MailIn(self.p.aq_parent,
            str(TestMessage(subject='[Some Page]')),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'Some Page')

    def testDestinationFromMultipleBracketedNamesInSubject(self):
        m = mailin.MailIn(
            self.p.aq_parent,
            str(TestMessage(subject='[Fwd:][LIST][Some Page]')),
            subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'Some Page')
    
    def testDestinationFromLongSubject(self):
        m = mailin.MailIn(
            self.p.aq_parent,
            str(TestMessage(subject='['+' ....'*20+'Test Page'+' ....'*20+']')),
            subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpage.pageName(),'TestPage')
    
    def testDestinationFromLongSubjectWithLineBreak(self):
        m = mailin.MailIn(
            self.p.aq_parent,
            str(TestMessage(subject='''\
Re: [IssueNo0547 mail (with long subject ?) may go to wrong page
 (test with long long long long long long subject)] property change''')),
            subscribersonly=0)
        m.decideDestination()
        self.assertEqual(
            m.destpagename,
            'IssueNo0547 mail (with long subject ?) may go to wrong page (test with long long long long long long subject)')
    
    def testDestinationWithBlankRealName(self):
        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='wiki@b.c (   )',
            subject='SomePage',
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,THISPAGE)

    def testDestinationWithNoWordsInRealName(self):
        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='wiki@b.c (...)',
            subject='SomePage',
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,THISPAGE)

    def testDestinationRealNameStripping(self):
        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='wiki@b.c (  SomePage\t)',
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'SomePage')

    def testDestinationWithQuotesInRealName(self):
        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to="wiki@b.c ('SomePage')",
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'SomePage')
        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to='wiki@b.c ("SomePage")',
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,'SomePage')

    def testDestinationWithEmailInRealName(self):
        m = mailin.MailIn(self.p.aq_parent,str(TestMessage(
            to="wiki@b.c (wiki@b.c)",
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,THISPAGE)

    def testDestinationFromPageContext(self):
        m = mailin.MailIn(self.p,str(TestMessage(
            to='a@b.c (SomePage)',
            subject='[SomePage] SomePage',
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.destpagename,THISPAGE)

    def testDestinationFromTrackerAddress(self):
        m = mailin.MailIn(self.p,str(TestMessage(
            to='bugs@b.c',
            )),subscribersonly=0)
        m.decideDestination()
        self.assertEqual(m.trackerissue,1)

    def testSubscriberMailin(self):
        old = self.p.text()
        self.p.subscribe(TESTSENDER)
        mailin.mailin(self.p,TESTMSG)
        self.assertEqual(1, len(re.findall(TESTBODY,self.p.text())))
        
    def testNonSubscriberMailinFails(self):
        old = self.p.text()
        mailin.mailin(self.p,TESTMSG)
        self.assertEqual(old, self.p.read())
        
    def testNonSubscriberMailinWithOpenPosting(self):
        old = self.p.text()
        mailin.mailin(self.p,TESTMSG,subscribersonly=0)
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
        mailin.mailin(self.p,TESTMSG,trackerissue=1,subscribersonly=0)
        self.checkAddIssueRequest(self.p.aq_parent.issuetracker_request)

    # this works.. need a functional test which sends through mail
    def testMailinTrackerIssueLongSubject(self):
        longsubjmsg = str(TestMessage(subject=LONGSUBJECT))
        mailin.mailin(self.p,longsubjmsg,trackerissue=1,subscribersonly=0)
        self.checkAddIssueRequest(self.p.aq_parent.issuetracker_request,
                                  newtitle=LONGSUBJECT)

    def checkAddIssueRequest(self,req,newtitle=TESTSUBJECT,newtext=TESTBODY):
        self.assert_(hasattr(req,'newtitle'))
        self.assertEqual(req.newtitle, newtitle)
        self.assert_(hasattr(req,'newtext'))
        self.assertEqual(req.newtext, newtext)
        self.assert_(hasattr(req,'submitted'))
        self.assertEqual(req.submitted, 1)

    def testStripSignature(self):
        # signatures after -- should be stripped
        self.assertEqual(
            mailin.MailIn(self.p.aq_parent,str(TestMessage())).stripSignature(
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
            mailin.MailIn(self.p.aq_parent,str(TestMessage())).stripSignature(
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
            mailin.MailIn(self.p.aq_parent,str(TestMessage())).stripSignature(
            '''blah
---
blah'''),
            '''blah
---
blah''')
        self.assertEqual(
            mailin.MailIn(self.p.aq_parent,str(TestMessage())).stripSignature(
            '''blah
 --
blah'''),
            '''blah
 --
blah''')


        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MailinTests))
    return suite

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__ == '__main__':
    main()
