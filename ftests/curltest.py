import os, sys, re
from string import split, strip
import time
import commands
import unittest

class TestBase(unittest.TestCase):
    """
    Temporary site testing utilities. 
    """
    def authFrom(self,user,password):
        if user and password:
            return '-u%s:%s' % (user,password)
        elif user:
            return '-u%s -n' % (user)
        else:
            return '-n'

    def getPage(self,url,user=None,password=None):
        auth = self.authFrom(user,password)
        #print('\ncurl -sL %s %s' % (auth, url))
        return commands.getoutput('curl -sL %s %s' % (auth, url))

    def getHead(self,url,user='',password=''):
        auth = self.authFrom(user,password)
        return commands.getoutput('curl -sL -I %s %s' % (auth, url))

    def getFirstByte(self,url,user='',password=''):
        auth = self.authFrom(user,password)
        return commands.getoutput('curl -sL %s -r0-0 %s' % (auth, url))

    def postComment(self,url,text='test',subject='[test]',
                    user='',password=''):
        auth = self.authFrom(user,password)
        return commands.getoutput(
            'curl -sL %s -Fuse_heading=1 -F"subject_heading=%s" -Ftext=%s %s/comment' \
            % (auth,subject,text,url))

    def setPreferences(self,email='',delivery='',user='',password=''):
        auth = self.authFrom(user,password)
        return commands.getoutput(
            'curl -sL %s -Femail=%s delivery=%s %s' \
            % (auth,email,delivery,PREFSURL))

    def assertNoError(self,page):
        self.assert_(not re.search(r'Site Error',page))
        self.assert_(not re.search(r'(Unauthorized|You are not authorized)',page))

    def assertPageOk(self,page):
        self.assertNoError(page)
        self.assert_(re.search(r'(?i)you are here',page))

    def assertContains(self,text,pattern):
        self.assert_(re.search(pattern,text))

    def assertDoesNotContain(self,text,pattern):
        self.failIf(re.search(pattern,text))

    def assertPageContains(self,page,pattern,user=None,password=None):
        self.assertContains(self.getPage(page,user,password),pattern)

    def assertPageDoesNotContain(self,page,pattern,user=None,password=None):
        self.assertDoesNotContain(self.getPage(page,user,password),pattern)

