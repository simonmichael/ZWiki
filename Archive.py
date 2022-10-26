"""
An archive for the wiki. This is a separate, read-only sub-wiki where
pages or groups of pages can be dumped to put them out of the way,
without deleting entirely.
"""

from AccessControl import getSecurityManager, ClassSecurityInfo
import AccessControl.Permissions
try: from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2 as Folder
except ImportError: from OFS.Folder import Folder # zope 2.7
from AccessControl.class_init import InitializeClass

from OutlineSupport import PersistentOutline
import Permissions
from Utils import safe_hasattr, sorted, registerSupportFolderId, BLATHER
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
            
    security.declareProtected(AccessControl.Permissions.delete_objects, 'archive')
    def archive(self, REQUEST=None, pagename=None):
        """Move this page, and all offspring solely parented under this
        page, to the archive subfolder.  This has no effect if called on a
        page already in the archive folder, or a non-ZODB object (such as
        a temporary page object created by plone's portal_factory).
        As with delete, if a pagename argument is provided, redirect all
        incoming wiki links there.

        NB this requires 'Delete objects' permission on the wiki folder.
        """
        if self.inArchiveFolder() or inPortalFactory(self): return
        self.ensureArchiveFolder()
        f, af, rf = self.folder(), self.archiveFolder(), self.revisionsFolder()

        # which pages to move
        oids = self.offspringIdsAsList()
        id = self.getId()
        ids = [id] + oids
        def notParentedElsewhere(id):
            pids = [self.pageWithName(p).getId() for p in self.pageWithId(id).getParents()]
            for p in pids:
                if not p in ids: return False
            return True
        ids2 = [id] + filter(notParentedElsewhere, oids)
        # and their revisions
        rids = []
        for i in ids2: rids.extend(self.pageWithId(i).oldRevisionIds())

        if pagename and strip(pagename):
            self._replaceLinksEverywhere(oldname,pagename,REQUEST)

        # where to go afterward - up, or to default page (which may change)
        redirecturl = self.primaryParent() and self.primaryParentUrl() or None

        # XXX disable outline cache creation with similar kludge to saveRevision's
        saved_manage_afterAdd                = self.__class__.manage_afterAdd
        self.__class__.manage_afterAdd = lambda self,item,container:None

        # move pages and revisions
        af.manage_pasteObjects(f.manage_cutObjects(ids2), REQUEST)
        if rids:
            af[id].ensureRevisionsFolder()
            af[id].revisionsFolder().manage_pasteObjects(rf.manage_cutObjects(rids), REQUEST)

        self.__class__.manage_afterAdd = saved_manage_afterAdd

        # log, notify, redirect
        msg = 'archived %s' % self.pageName() \
              + (len(oids) and ' and %d subtopics' % len(oids) or '') \
              + (len(rids) and ' and %d revisions' % len(rids) or '')
        BLATHER(msg)
        self.sendMailToEditSubscribers(
            msg+'\n',
            REQUEST=REQUEST,
            subject='(archived)')
        redirecturl = redirecturl or self.defaultPageUrl()
        if REQUEST: REQUEST.RESPONSE.redirect(redirecturl)


InitializeClass(ArchiveSupport)
