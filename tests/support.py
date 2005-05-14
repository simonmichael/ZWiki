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

    WARNING: this sets self.page.request at the beginning of the test.
    If you replace it with a new one, be sure to set page.request again
    and not just past REQUEST as an argument to avoid confusing DTML.
    
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
    #disableI18nForUnitTesting()

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
    def __init__(self,language=None):
        resp = HTTPResponse(stdout=sys.stdout)
        environ={}
        environ['SERVER_NAME']='foo'
        environ['SERVER_PORT']='80'
        environ['REQUEST_METHOD'] = 'GET'
        environ['SCRIPT_NAME']='/foo/test'
        environ['SESSION']=None
        self.SESSION={}
        HTTPRequest.__init__(self,None,environ,resp)
        if language: self.setLanguage(language)
    def setLanguage(self,language):
        self.environ['HTTP_ACCEPT_LANGUAGE']=language
        
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

def mockPage(source_string='', mapping=None, __name__='TestPage', folder=None):
    """
    Generate a mock zwiki page with a realistic acquisition context.
    """
    page = MockZWikiPage(source_string=source_string,
                         mapping=mapping,
                         __name__=__name__)
    # situate the page in a folder, making it out of thin air if needed
    if not folder:
        folder = OFS.Folder.Folder()
        folder.aq_base = folder.aq_inner = folder
        folder.aq_parent = None
    id = folder._setObject(page.getId(), page, set_owner=0)
    # make sure self.REQUEST works in folder context also
    folder.REQUEST = page.REQUEST
    return folder[id]

class MockZWikiPage(ZWikiPage):
    """
    A mock ZWikiPage object for use in testing.

    Notes:
    - use mockPage() to instantiate these with a real acquisition context
    - some zopish things don't work and are too much work to mock
    - much time wasted debugging obscure mockup-related problems
    """
    def __init__(self, source_string='', mapping=None, __name__='TestPage'):
        apply(ZWikiPage.__init__,(self,source_string,mapping,__name__))
        self.REQUEST = MockRequest()

    def checkPermission(self, permission, object): return 1

    def cb_isMoveable(self): return 1
        
    ZopeTime = DateTime.DateTime


# neutralize PTS to get most tests working.. see also testI18n.py
def disableI18nForUnitTesting(): 
    try:
        from Products.PlacelessTranslationService.PlacelessTranslationService \
             import PlacelessTranslationService
        PlacelessTranslationService._getContext = \
            lambda self,context: MockRequest()
        PlacelessTranslationService.negotiate_language = \
            lambda self,context,domain: 'en'
        #from Products.ZWiki import I18nSupport
        #I18nSupport._ = lambda s:str(s)
    except ImportError:
        pass

disableI18nForUnitTesting()
