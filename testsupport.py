"""
Common initialization and support classes for zwiki unit tests.

Zwiki core and plugin test modules (_tests.py) import everything from
here, then they are pretty much ready to go, except for installing
whichever zope products they need. (We let each test module install
just it's required products so that individual tests may be run more
quickly.)

what is the reason for using afterSetUp instead of setUp ? 

XXX various, too many test fixture classes are used in zwiki tests right now:
- ZwikiTestCase
- PloneTestCase
- ZopeTestCase
- TestCase

"""

import sys, re, unittest

import OFS, DateTime
from Testing import ZopeTestCase
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse

from Products.ZWiki.ZWikiPage import ZWikiPage
from Products import ZWiki


def afterSetUp(self):
    """
    Do common setup for our ZopeTestCase-based unit tests.

    This is a function so that it can be called by both our
    ZopeTestCase and PloneTestCases's afterSetUp method.
    XXX ?

    WARNING: this sets self.page.request at the beginning of the test.
    If you replace it with a new one, be sure to set page.request again
    and not just past REQUEST as an argument to avoid confusing DTML.
    XXX pardon ?
    """
    # grant all zwiki permissions by default
    from Products.ZWiki import Permissions
    #from Products.CMFCore import CMFCorePermissions
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
        #CMFCorePermissions.AddPortalContent,
        ])
    # set up a wiki in a subfolder, with one page of default type (RST)
    self.folder.manage_addFolder('wiki',title='')
    self.wiki = self.folder.wiki
    self.wiki.manage_addProduct['ZWiki'].manage_addZWikiPage('TestPage')
    self.p = self.page = self.wiki.TestPage
    # our mock request seems a bit more useful than ZTC's
    #self.request = self.app.REQUEST
    self.request = self.page.REQUEST = MockRequest()
    #self.request.cookies['zwiki_username'] = 'test'

class ZwikiTestCase(ZopeTestCase.ZopeTestCase):
    afterSetUp = afterSetUp

    
# mock objects

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
    def checkPermission(self, permission, object):
        return 1
    def cb_isMoveable(self):
        return 1
    ZopeTime = DateTime.DateTime

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


# if PTS is installed, disabled it to let tests run.. I18n_tests.py will
# test it directly
try:
    from Products.PlacelessTranslationService.PlacelessTranslationService \
         import PlacelessTranslationService
    PlacelessTranslationService._getContext = \
        lambda self,context: MockRequest()
    PlacelessTranslationService.negotiate_language = \
        lambda self,context,domain: 'en'
    #from Products.ZWiki import I18n
    #I18n._ = lambda s:str(s)
except ImportError:
    pass
