# CMF/Plone compatibility
# See also __init__.py and Extensions/Install.py

#from types import *
from Globals import InitializeClass
from Utils import safe_hasattr

try:
    from Products import CMFCore
    CMFCore = CMFCore # pyflakes
    HAS_CMF = True
except ImportError:
    HAS_CMF = False

try:
    from Products import CMFPlone
    CMFPlone = CMFPlone # pyflakes
    HAS_PLONE = True
except ImportError:
    HAS_PLONE = False

# XXX also need to skip when running unit tests ?
if not HAS_CMF:    
    class PageCMFSupport:
        __implements__ = ()
        def supportsCMF(self): return 0
        def inCMF(self): return 0
        def inPlone(self): return 0

else:
    from AccessControl import ClassSecurityInfo
    from OFS.DTMLDocument import DTMLDocument
    from Products.CMFCore.PortalContent import PortalContent
    from Products.CMFDefault.SkinnedFolder import SkinnedFolder
    from Products.CMFDefault.DublinCore import DefaultDublinCoreImpl
    from DateTime import DateTime
    import Permissions
    from Defaults import PAGE_PORTALTYPE

    # backwards compatibility
    class WikiFolder(SkinnedFolder):
        meta_type='Wiki Folder'
        security = ClassSecurityInfo()
        security.declarePublic('allowedContentTypes')
        def allowedContentTypes( self ):
            return []
    InitializeClass(WikiFolder)
        
    class ZwikiDublinCoreImpl(DefaultDublinCoreImpl):
        """
        Zwiki's implementation of Dublin Core.

        We use our own similar attributes..
        XXX maybe we can always use dublin core and simplify.
        """
        __implements__ = DefaultDublinCoreImpl.__implements__ 

        security = ClassSecurityInfo()
        security.declarePrivate('setModificationDate')
        def setModificationDate(self, modification_date=None):
            if modification_date is None:
                self.last_edit_time = DateTime().ISO8601()
            else:
                self.last_edit_time = self._datify(modification_date).ISO8601()

        security.declarePublic('modified')
        def modified(self):
            return self.lastEditTime()

        security.declarePublic('Creator')
        def Creator(self):
            return self.creator

        security.declarePublic('Description')
        def Description(self):
            return self.summary()

        security.declarePublic( 'CreationDate' )
        def CreationDate(self):
            return self.creationTime().ISO8601()

        security.declarePublic( 'getPageTitle' )
        def getPageTitle(self, here=None, template=None, portal_title=None):
            """
            Return the proper name of this page for use by Plone.

            A quick fix for plone's script, which doesn't like using
            our page's title when it's the same as the id.
            XXX file a bug
            """
            return self.toencoded(self.pageName())
        

    InitializeClass(ZwikiDublinCoreImpl)

    class PageCMFSupport(PortalContent, ZwikiDublinCoreImpl):
        """
        Mix-in class for CMF support
        """
        __implements__ = ZwikiDublinCoreImpl.__implements__ + \
                         PortalContent.__implements__
   
        portal_type = PAGE_PORTALTYPE
        # provide this so DublinCore.Format works with old instances
        format = 'text/html'

        # permission defaults
        security = ClassSecurityInfo()
        set = security.setPermissionDefault
        set(Permissions.Edit, ('Owner', 'Manager', 'Authenticated'))
        set(Permissions.FTPRead, ('Owner', 'Manager'))
        set(Permissions.Add, ('Owner', 'Manager', 'Authenticated'))
        #set(Permissions.Move, ('Owner', 'Manager'))
        set(Permissions.Comment, ('Owner', 'Manager', 'Authenticated'))
        set = None

        security.declarePublic('supportsCMF')
        def supportsCMF(self):
            return 1

        security.declarePublic('inCMF')
        def inCMF(self):
            """return true if this page is in a CMF site"""
            return safe_hasattr(self.aq_inner.aq_parent,'portal_membership')

        security.declarePublic('inPlone')
        def inPlone(self):
            """return true if this page is in a Plone site"""
            return self.inCMF() and safe_hasattr(self.aq_inner.aq_parent,'plone_utils')

        def __init__(self, source_string='', mapping=None, __name__=''):
            DTMLDocument.__init__(self,
                                  source_string=source_string,
                                  mapping=mapping,
                                  __name__=__name__,
                                  )
            ZwikiDublinCoreImpl.__init__(self)

        security.declarePublic('getId')
        def getId(self):
            try: return self.id()
            except TypeError: return self.id

        # Disabled so we can set the subject from Plone's Metadata view
        #security.declareProtected(Permissions.View, 'Subject')
        #def Subject(self):
        #    return self.spacedPageName()

        security.declareProtected(Permissions.View, 'Description')
        def Description(self):
            return self.summary()

        def wiki_context(self, REQUEST=None, with_siblings=0):
            return self.context(REQUEST, with_siblings)

        # Zwiki pages are different from other portal content; for one
        # thing, we follow the Zwiki: * permissions (ignoring eg Modify
        # portal content) so we need to reflect those. Also because we
        # have some key UI functions up there in the edit border (history,
        # backlinks, subscription), we will almost always need to show it.
        # Which is a pity, as (a) pages look nicer without it, and (b) in
        # the plone UI it signifies edit access, and we might not be
        # permitting that.  Better ideas welcome. For now we will just
        # force it always on.
        # Also note Plone 2.1.0 unconditionally hides the green border for
        # anonymous users, which is a bug. In future they will probably
        # check for the modify portal content and review permissions first.
        def showEditableBorder(self,**args):
            """Always show the green border; Zwiki's current UI needs it."""
            return 1

        def isDefaultPageInFolder(self):
            """ Returns a boolean indicating whether the current context is the
                default page of its parent folder.

                Plone 2.5 wants this. It's used (so far) to disable
                plone's cut/copy/paste/rename actions for the default
                page. I guess this suits Zwiki's default (front) wiki
                page.
            """
            return self == self.defaultPage()

            
InitializeClass(PageCMFSupport)

