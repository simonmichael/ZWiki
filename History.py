"""
Permanent revision history for zwiki pages.
"""

from AccessControl import getSecurityManager, ClassSecurityInfo
from Globals import InitializeClass

import re
import Permissions
from OutlineSupport import PersistentOutline

class PageHistorySupport:
    """
    This mixin provides methods to save, browse and restore zwiki page
    revisions.  Unlike zope's built-in transaction history, these
    revisions are saved forever, as page copies in a subfolder.
    """
    security = ClassSecurityInfo()

    security.declareProtected(Permissions.View, 'revision')
    def revision(self):
        """This page's revision number, starting from 1."""
        return self.revisionCount()

    security.declareProtected(Permissions.View, 'revisionCount')
    def revisionCount(self):
        """The number of known revisions for this page."""
        return len(self.revisions())

    security.declareProtected(Permissions.View, 'revisions')
    def revisions(self):
        """A list of this page's revisions, oldest first, current page last."""
        return self.oldRevisions() + [self]

    def oldRevisions(self):
        f = self.revisionsFolder()
        if not f: return []
        rev = re.compile(r'%s\.\d+$' % self.getId()).match
        return [p for p in f.objectValues(spec='ZWiki Page') if rev(p.getId())]

    def revisionsFolder(self):
        if hasattr(self.folder().aq_base, 'revisions'):
            f = self.folder().revisions
            if f.isPrincipiaFolderish:
                return f
        return None
            
    def ensureRevisionsFolder(self):
        if not hasattr(self.folder().aq_base,'revisions'):
            self.folder().manage_addFolder('revisions', 'wiki page revisions')

    def saveRevision(self, REQUEST=None):
        """
        Save a snapshot of this page in the revisions folder.

        The folder will be created if necessary.
        """
        f = self.folder()
        cb = f.manage_copyObjects(self.getId())
        self.ensureRevisionsFolder()

        # kludge so the following paste & rename operations won't meddle
        # with the catalog or page hierarchy (hopefully thread-safe,
        # otherwise escalate to "horrible kludge"):
        manage_afterAdd = self.__class__.manage_afterAdd
        self.__class__.manage_afterAdd = lambda self,item,container: None
        wikiOutline = self.__class__.wikiOutline
        self.__class__.wikiOutline = lambda self: PersistentOutline()

        self.revisionsFolder().manage_pasteObjects(cb)
        # add revision number to the id
        rid = '%s.%d' % (self.getId(), self.revision())
        self.revisionsFolder().manage_renameObjects([self.getId()],[rid])

        self.__class__.manage_afterAdd = manage_afterAdd
        self.__class__.wikiOutline = wikiOutline


InitializeClass(PageHistorySupport)
