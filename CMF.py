# CMF compatibility
# this is split between CMF.py, CMFInit.py and Extensions/cmf_install_zwiki.py
# (unfortunately) and it's still not right (need to import makeWikiPage
# for PUT_factory ?). 
# move CMFInstall into the skin ?

# fails when running unit tests
# keep the try out of ZWikiPage.py to help imenu
try:
    from types import *
    import string, re, os
    from AccessControl import ClassSecurityInfo
    from Acquisition import aq_base, aq_inner, aq_parent
    from Globals import InitializeClass
    from OFS.DTMLDocument import DTMLDocument
    from Products.CMFCore.PortalContent import PortalContent
    from Products.CMFCore.utils import _getViewFor
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
        security = ClassSecurityInfo()
        security.declarePrivate('setModificationDate')
        def setModificationDate(self, modification_date=None):
            if modification_date is None:
                self.last_edit_time = DateTime().ISO()
            else:
                self.last_edit_time = self._datify(modification_date).ISO()

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

    InitializeClass(ZwikiDublinCoreImpl)

    class CMFAwareness(PortalContent, ZwikiDublinCoreImpl):
        """
        Mix-in class for CMF support
        """
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
            return self.text()

        #security.declareProtected(Permissions.View, '__call__')
        #def __call__(self, client=None, REQUEST={}, RESPONSE=None, **kw):
        #    '''
        #    Invokes the default view.
        #    '''
        #    view = _getViewFor( self )
        #    if getattr(aq_base(view), 'isDocTemp', 0):
        #        return apply(view, (self, REQUEST))
        #    else:
        #        if REQUEST:
        #            kw[ 'REQUEST' ] = REQUEST
        #        if RESPONSE:
        #            kw[ 'RESPONSE' ] = RESPONSE
        #        return apply( view, (self,), kw )

        # needed ?
        #index_html = None  # This special value informs ZPublisher to use __call__

        def wiki_context(self, REQUEST=None, with_siblings=0):
            return self.context(REQUEST, with_siblings)

except ImportError:
    class CMFAwareness:
        def supportsCMF(self): return 0
        def inCMF(self): return 0

InitializeClass(CMFAwareness)

