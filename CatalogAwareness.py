# catalog awareness for zwiki pages
# based on Casey Duncan's DTMLDocumentExt 0.1
#
# todo: may want to make these all safe against Catalog errors

import string
from Utils import BLATHER
from AccessControl import getSecurityManager, ClassSecurityInfo
import Permissions

###########################################################################
# CLASS CatalogAwareness
###########################################################################

class CatalogAwareness:
    """
    Holds most of ZWikiPage's catalog awareness code.
    Zope's CatalogAwareness didn't work for me and this one
    is a little more flexible or at least familiar.
    """
    security = ClassSecurityInfo()

    NOT_CATALOGED=0
    _properties=(
        {'id':'NOT_CATALOGED', 'type': 'boolean', 'mode': 'w'},
        )

    def isCatalogable(self):
        return not getattr(self, 'NOT_CATALOGED', 0)

    def catalog(self):
        """
        Return the catalog object used by this page, if any.

        By default, Zwiki looks for an object named 'Catalog' in this wiki
        folder (will not acquire) or a 'portal_catalog' (can acquire).

        If a SITE_CATALOG property exists (can acquire), Zwiki will look
        for an object by that name (can acquire); if no such object
        exists, or SITE_CATALOG is blank, no catalog will be used.
        """
        folder = self.folder()
        folderaqbase = getattr(folder,'aq_base',
                               folder) # make tests work
        if not hasattr(self,'SITE_CATALOG'):
            if hasattr(folderaqbase,'Catalog'):
                return folder.Catalog
            else:
                return getattr(folder,'portal_catalog',None)
        else:
            return getattr(folder,self.SITE_CATALOG,None)

    security.declareProtected('Manage properties', 'hasCatalog')
    def hasCatalog(self):
        """Is this page keeping itself indexed in a catalog ?"""
        return self.catalog() != None

    security.declareProtected(Permissions.manage_properties, 'catalogid')
    def catalogId(self):
        """
        Give the id of the catalog used by this page, or "NONE".

        Should be useful for troubleshooting. Requires manage properties
        permission. Not the same as the old getCatalogId.
        """
        if self.hasCatalog(): return self.catalog().getId()
        else: return 'NONE'

    def hasCatalogIndexesMetadata(self,indexesAndMetadata):
        """
        Do we have a catalog with these indexes and metadata ?

        It's good to check that an index exists before searching,
        otherwise we'll get the entire catalog contents.
        indexesAndMetadata is two lists of strings, eg:
        (['index1','index2'],['metadata1'])
        """
        catalog = self.catalog()
        if not catalog: return 0
        catalogindexes, catalogmetadata = catalog.indexes(), catalog.schema()
        indexes, metadata = indexesAndMetadata
        for i in indexes:
            if not i in catalogindexes: return 0
        for i in metadata:
            if not i in catalogmetadata: return 0
        return 1

    def searchCatalog(self,**kw):
        """
        Searches this wiki page's catalog if any, passing through arguments.
        """
        if self.hasCatalog(): return self.catalog()(**kw)
        else: return None

    def updateCatalog(self):
        """
        Update this page's catalog entry if needed, and log problems.

        XXX todo: also, make it easy to update individual indexes
        """
        try: self.index_object()
        except:
            # XXX should show a traceback 
            BLATHER('failed to index '+self.id())
            #what is this retry cruft
            #BLATHER('failed to index '+p.id()+', trying reindex')
            #try: p.reindex_object()
            #except: BLATHER('failed to reindex '+p.id()+', giving up')

    def url(self):
        """Return the absolute object path"""
        return string.join(self.getPhysicalPath(),'/')

    getPath = url

    def index_object(self,log=1):
        """A common method to allow Findables to index themselves."""
        if (self.hasCatalog() and self.isCatalogable()):
            if log: BLATHER('indexing',self.url(),'in',self.catalog().getId())
            #BLATHER(self.id(),"'s last_edit_time is",self.last_edit_time)
            self.catalog().catalog_object(self, self.url())
            self.is_indexed_ = 1
            #BLATHER('indexing '+self.id()+'done')

    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        #BLATHER('unindexing '+self.id())
        if self.hasCatalog():
            self.catalog().uncatalog_object(self.url())
            self.is_indexed_ = 0

    def reindex_object(self):
        """Reindex the object in the Catalog"""
        if getattr(self, 'is_indexed_', 0):
            self.unindex_object()
        self.index_object()

# enable catalog awareness for common ZMI operations
# have to do this in __init__ because of an import loop ?
