"""
An archive for the wiki. This is a separate, read-only sub-wiki where
pages or groups of pages can be dumped to put them out of the way,
without deleting entirely.
"""

from AccessControl import getSecurityManager, ClassSecurityInfo
try: from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2 as Folder
except ImportError: from OFS.Folder import Folder # zope 2.7
from Globals import InitializeClass
from OutlineSupport import PersistentOutline
import Permissions
from Utils import safe_hasattr, sorted, registerSupportFolderId
import re

def inPortalFactory(self): return self.inCMF() and self.folder().getId() == 'portal_factory'

ARCHIVE_FOLDER_ID = 'archive'
registerSupportFolderId(ARCHIVE_FOLDER_ID)

class ArchiveSupport:
    """
    This mixin provides methods to move pages or groups of pages to and
    from the wiki archive.
    """
    security = ClassSecurityInfo()

    def ensureArchiveFolder(self):
        if self.archiveFolder() is None:
            self.folder()._setObject(ARCHIVE_FOLDER_ID,Folder(ARCHIVE_FOLDER_ID))

    def inArchiveFolder(self):
        return self.folder().getId() == ARCHIVE_FOLDER_ID

    def archiveFolder(self):
        """Get the archive subfolder, even called from within it."""
        if self.inArchiveFolder():
            return self.folder()
        elif safe_hasattr(self.folder().aq_base, ARCHIVE_FOLDER_ID):
            f = self.folder()[ARCHIVE_FOLDER_ID]
            if f.isPrincipiaFolderish:
                return f
        return None
            
    # def wikiFolder(self):
    #     """Get the main wiki folder, even if called on a revision object."""
    #     if self.inRevisionsFolder():
    #         f = self.folder()
    #         # like folder()
    #         return getattr(getattr(f,'aq_inner',f),'aq_parent',None)
    #     else:
    #         return self.folder()

    security.declareProtected(Permissions.Archive, 'archive')
    def archive(self, REQUEST=None, pagename=None):
        """Move this page, and all offspring solely parented under this
        page, to the archive subfolder.  This has no effect if called on a
        page already in the archive folder, or a non-ZODB object (such as
        a temporary page object created by plone's portal_factory).
        As with delete, if a pagename argument is provided, redirect all
        incoming wiki links there.
        """
        if self.inArchiveFolder() or inPortalFactory(self): return
        self.ensureArchiveFolder()
        oids = self.offspringIdsAsList()
        ids = [self.getId()] + oids
        def notParentedElsewhere(id):
            pids = [self.pageWithName(p).getId() for p in self.pageWithId(id).getParents()]
            for p in pids:
                if not p in ids: return False
            return True
        ids2 = [self.getId()] + filter(notParentedElsewhere, oids)

        if pagename and strip(pagename):
            self._replaceLinksEverywhere(oldname,pagename,REQUEST)

        # XXX disable outline cache creation with similar kludge to saveRevision's
        saved_manage_afterAdd                = self.__class__.manage_afterAdd
        self.__class__.manage_afterAdd = lambda self,item,container:None
        self.archiveFolder().manage_pasteObjects(
            self.folder().manage_cutObjects(ids2, REQUEST), REQUEST)
        self.__class__.manage_afterAdd = saved_manage_afterAdd


InitializeClass(ArchiveSupport)


