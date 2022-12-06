"""
Common initialization and support classes for zwiki unit tests.

Zwiki core and plugin test modules (_tests.py) import everything from
here, then they are pretty much ready to go, except for installing
whichever zope products they need. (We let each test module install
just it's required products so that individual tests may be run more
quickly.)

NOTES

* what is the reason for using afterSetUp instead of setUp ?

* too many test fixture variants are used in zwiki tests right now:
- ZwikiTestCase
- PloneTestCase
- ZopeTestCase
- TestCase

* testing challenges
Some things are hard to do quickly and prevent tests being written. The
following would be good to figure out and make easy:

** low-level copy/move
   being able to copy/move objects, without security checks, with control
   over catalog & wiki outline updating
** access control testing
   being able to configure permissions and test that certain operations
   succeed/fail
** rendering views
   calling a view method like diff() fails trying to render the master template

* http://plone.org/documentation/how-to/reducing-unit-test-times
"""

import sys, re, unittest, doctest

import OFS, DateTime
from Testing import ZopeTestCase
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
import AccessControl.Permissions

from Products import ZWiki
from Products.ZWiki.ZWikiPage import ZWikiPage
from Products.ZWiki.Utils import safe_hasattr


# pickling REQUEST causes problems for tests
def __getstate__(self):
    odict = self.__dict__.copy()
    try: del odict['REQUEST']
    except KeyError: pass
    return odict
ZWikiPage.__getstate__ = __getstate__


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
        AccessControl.Permissions.copy_or_move,
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
    # kludge.. some recent test exercises code that commits and so
    # this is required for cleanup, except after test_dtml_in_rst
    def beforeClose(self):
        try:
            import transaction; transaction.commit()
        except TypeError:
            pass


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
    A mock ZWikiPage object used by some tests.

    Notes:
    - use mockPage() to instantiate these with a real acquisition context
    - some zopish things don't work and are too much work to mock
    - much time wasted debugging obscure mockup-related problems,
      hardly worth bothering with imho
    """
    def __init__(self, source_string='', mapping=None, __name__='TestPage'):
        apply(ZWikiPage.__init__,(self,source_string,mapping,__name__))
        self.REQUEST = MockRequest()
    def checkPermission(self, permission, object): return 1
    def cb_isMoveable(self): return 1
    def cb_isCopyable(self): return 1
    def getPhysicalRoot(self): return self.folder()
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
