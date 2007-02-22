# CMF compatibility
# this is split between CMF.py, CMFInit.py and Extensions/cmf_install_zwiki.py
# (unfortunately) and it's still not right (need to import makeWikiPage
# for PUT_factory ?). 
# move CMFInstall into the skin ?

from types import *
import string, re, os
from Globals import InitializeClass

try:
    from Products import CMFCore
    HAS_CMF = 1
except ImportError:
    HAS_CMF = 0

# XXX also need to skip when running unit tests ?
if not HAS_CMF:    
    class PageCMFSupport:
        __implements__ = ()
        def supportsCMF(self): return 0
        def inCMF(self): return 0

else:
    from AccessControl import ClassSecurityInfo
    from Acquisition import aq_base, aq_inner, aq_parent
    from OFS.DTMLDocument import DTMLDocument
    from Products.CMFCore.PortalContent import PortalContent
    from Products.CMFDefault.SkinnedFolder import SkinnedFolder
    from Products import CMFDefault
    from Products.CMFDefault.DublinCore import DefaultDublinCoreImpl
    from AccessControl import getSecurityManager, ClassSecurityInfo
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
                self.last_edit_time = DateTime().toZone('UTC').ISO()
            else:
                self.last_edit_time = self._datify(modification_date).toZone('UTC').ISO()

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
            return self.creationTime().ISO()

        security.declarePublic( 'getPageTitle' )
        def getPageTitle(self, here=None, template=None, portal_title=None):
            """
            Return the proper name of this page for use by Plone.

            A quick fix for plone's script, which doesn't like using
            our page's title when it's the same as the id.
            XXX file a bug
            """
            return self.pageName()
        

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
            """return true if this page is in a CMF portal"""
            return hasattr(self.aq_inner.aq_parent,'portal_membership')

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

        security.declareProtected(Permissions.View, 'SearchableText')
        def SearchableText(self):
         """Return the main searchable fields concatenated for easy indexing.

         Used by eg Plone's livesearch.
         """
         # XXX how naive to think this could work.. wait for the unicode errors
         return '%s\n%s' % (self.pageName(), self.text())
         #example from AT:
         #if type_datum is UnicodeType:
         #    datum = datum.encode(charset)
         #datum = "%s %s" % (datum, vocab.getValue(datum, ''), )

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

