# common initialization and support classes for zwiki unit tests

import string, re, os, sys, pdb
import unittest
from Testing.makerequest import makerequest

# allow INSTANCE_HOME products to be imported from Products
# ZopeTestCase also claims to do this, but it doesn't
# work with normal zope, testrunner, python testModule.py, python1.5, python2..
# Unfortunately testrunner clobbers INSTANCE_HOME, so we'll assume it's
# the grandparent of the current directory. But this gets confused by
# symbolic links.
import os
def pdir(path): return os.path.split(path)[0]
thisProductsDir = pdir(pdir(pdir(os.path.abspath(__file__))))
import Products
Products.__path__.insert(0,thisProductsDir)

def zwikiAfterSetUp(self):
    """
    Do common setup for our ZopeTestCase-based unit tests.

    self is a ZopeTestCase instance; this should be called from it's
    afterSetUp method.
    """
    # grant all zwiki permissions by default
    from Products.ZWiki import Permissions
    from Products.CMFCore import CMFCorePermissions
    self.setPermissions([
        Permissions.AddWiki,
        Permissions.Add,
        Permissions.Comment,
        Permissions.Edit,
        Permissions.ChangeType,
        Permissions.Delete,
        Permissions.Rate,
        Permissions.Rename,
        Permissions.Reparent,
        Permissions.Upload,
        Permissions.FTP,
        CMFCorePermissions.AddPortalContent,
        ])
    # set up a wiki in a subfolder, with one page
    self.folder.manage_addFolder('wiki',title='')
    self.wiki = self.folder.wiki
    self.wiki.manage_addProduct['ZWiki'].manage_addZWikiPage('TestPage')
    self.p = self.page = self.wiki.TestPage
    # our mock request seems a bit more useful than ZTC's
    #self.request = self.app.REQUEST
    self.request = self.page.REQUEST = MockRequest()

# can we go further and do this here:
#import os, sys
#if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
#ZopeTestCase.installProduct('ZCatalog')
#ZopeTestCase.installProduct('ZWiki')
#from Testing import ZopeTestCase
#class ZwikiTestCase(ZopeTestCase.ZopeTestCase):
#    def afterSetUp(self):
#        zwikiAfterSetUp(self)
# and then:
#class Tests(ZwikiTestCase):



# more non-ZTC tests support:

# needs to be imported early to set up Persistence.Persistent
import ZODB

# mock objects

from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
class MockRequest(HTTPRequest):
    """
    a mock HTTPRequest object for use in testing.

    like makerequest without the app dependency
    """
    def __init__(self):
        resp = HTTPResponse(stdout=sys.stdout)
        environ={}
        environ['SERVER_NAME']='foo'
        environ['SERVER_PORT']='80'
        environ['REQUEST_METHOD'] = 'GET'
        environ['SCRIPT_NAME']='/foo/test'
        HTTPRequest.__init__(self,None,environ,resp)

class MockUser:
    def __init__(self,username='testuser'):
        self.username = username
        class aclusers: pass
        self.acl_users = aclusers()
        self.acl_users._nobody = 'nobody'
    def getUserName(self):
        return self.username

#import OFS.ObjectManager, AccessControl.User
import OFS, DateTime
from Products import ZWiki
from Products.ZWiki.ZWikiPage import ZWikiPage
from Products.ZWiki.Mail import MailSupport

class MockZWikiPage(ZWikiPage):
    """
    A mock ZWikiPage object for use in testing.

    Problems, limitations:

    - we fake acquisition below, good enough for some tests. To get closer
    to the real thing, use p = MockZWikiPage().aq_parent.TestPage.  For
    the real thing, pass in a real folder (and call _setObject).

    - page methods like standard_wiki_header appear as attributes
    of the parent folder, breaking tests

    - some zopish things don't work and are too much work to mock.

    - time wasted debugging problems arising from use of this

    """
    def __init__(self, source_string='', mapping=None, __name__='TestPage',
                 folder=None,
                 **vars): # XXX change default name to MockPage ?
        apply(ZWikiPage.__init__,
              (self,source_string,mapping,__name__),vars)
        self.REQUEST = MockRequest()
        if folder:
            self._folder = folder
        else:
            self._folder = OFS.Folder.Folder()
            self._folder.aq_parent = None # no use (see testCreateWithFileUpload)
            self.aq_parent = self._folder
            self.aq_parent.__class__.manage_addFolder = OFS.Folder.manage_addFolder
            self.aq_inner = self
            self.aq_base = self
            self._folder._setObject(self.getId(),self,set_owner=0)

    # XXX can we do without ?
    #def getPhysicalPath(self): return ('',)

    def folder(self): return self._folder

    def checkPermission(self, permission, object):
        return 1

    ZopeTime = DateTime.DateTime

    def cb_isMoveable(self):
        return 1

    # MZP confuses the real isIssue
    def isIssue(self,client=None,REQUEST=None,RESPONSE=None,**kw):
        if (self.pageTypeId() == 'issuedtml' or 
            re.match(r'^IssueNo[0-9]+',self.title_or_id())):
            return 1
        else:
            return 0
