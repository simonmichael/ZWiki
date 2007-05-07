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
    are saved forever, as page objects in a revisions subfolder.
    """
    security = ClassSecurityInfo()

    security.declareProtected(Permissions.View, 'revision')
    def revision(self):
        """This page's revision number, starting from 1."""
        m = re.match(r'.*\.(\d+)', self.getId())
        if m:
            # I am a page revision object, get the revision from my id
            return int(m.group(1))
        else:
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
            self.folder().manage_addFolder( # XXX make it a btree
                'revisions',
                'wiki page revisions',
                REQUEST=getattr(self,'REQUEST',None))

    security.declareProtected(Permissions.View, 'pageRevision')
    def pageRevision(self, rev):
        """
        Get the specified previous revision of this page object.
        """
        return self.revisions()[int(rev)-1]

    def saveRevision(self, REQUEST=None):
        """
        Save a snapshot of this page in the revisions folder.

        The folder will be created if necessary.
        """
        self.ensureRevisionsFolder()
        rid = '%s.%d' % (self.getId(), self.revision())
        ob = self._getCopy(self.folder())
        ob._setId(rid)

        # kludge so the following won't update a catalog or outline cache
        # in the revisions folder (hopefully thread-safe, oherwise
        # escalate to "horrible kludge"):
        manage_afterAdd = self.__class__.manage_afterAdd
        wikiOutline     = self.__class__.wikiOutline
        self.__class__.manage_afterAdd = lambda self,item,container:None
        self.__class__.wikiOutline     = lambda self:PersistentOutline()

        self.revisionsFolder()._setObject(rid, ob)

        self.__class__.manage_afterAdd = manage_afterAdd
        self.__class__.wikiOutline     = wikiOutline

    def revisionBefore(self, username):
        """The revision number of the last edit not by username, or None."""
        for r in range(self.revisionCount(),0,-1):
            if self.pageRevision(r).last_editor != username:
                return r
        return None

    # backwards compatibility / temporary

    def forwardRev(self,rev): return self.revisionCount() - rev - 1

    def lastlog(self, rev=0, withQuotes=0):
        """
        Get the log note from an earlier revision of this page.

        Just a quick helper for diff browsing.
        """
        rev = self.forwardRev(int(rev))
        note = self.revisions()[rev].lastLog()
        match = re.search(r'"(.*)"',note)
        if match:
            if withQuotes: return match.group()
            else: return match.group(1)
        else:
            return ''

InitializeClass(PageHistorySupport)


