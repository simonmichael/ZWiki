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

    def revisionBefore(self, username):
        """The revision number of the last edit not by username, or None."""
        for r in range(self.revisionCount()):
            if self.revisionInfo(r)['last_editor'] != username:
                return r
        return None

    security.declareProtected(Permissions.Edit, 'revert')
    def revert(self, currentRevision, REQUEST=None):
        """
        Revert this page to the state of the specified revision.

        We do this by looking at the old page revision and applying a
        corrective edit to the current one. This will rename and reparent
        if needed, send a mailout, restore the old last edit time and
        record the reverter as last editor (XXX this should change, see
        issues #1157, #1293, #1324).

        Actually renames and reparents may no longer happen due to the new
        History.py revisions implementation; stand by.
        """
        if not currentRevision: return
        if not self.checkSufficientId(REQUEST):
            return self.denied(
                _("Sorry, this wiki doesn't allow anonymous edits. Please configure a username in options first."))
        old = self.pageRevision(currentRevision)
        self.setText(old.text())
        self.setPageType(old.pageTypeId())
        self.setVotes(old.votes())
        if self.getParents() != old.getParents():
            if not self.checkPermission(Permissions.Reparent, self):
                raise 'Unauthorized', (
                    _('You are not authorized to reparent this ZWiki Page.'))
            self.setParents(old.getParents())
            self.updateWikiOutline()
        if self.pageName() != old.pageName():
            if not self.checkPermission(Permissions.Rename, self):
                raise 'Unauthorized', (
                    _('You are not authorized to rename this ZWiki Page.'))
            self.rename(old.pageName())
        self.setLastEditor(REQUEST)
        self.last_edit_time = old.last_edit_time
        self.setLastLog('revert')
        self.index_object()
        self.sendMailToEditSubscribers(
            'This page was reverted to the %s version.\n' % old.last_edit_time,
            REQUEST=REQUEST,
            subjectSuffix='',
            subject='(reverted)')
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(self.pageUrl())

    security.declareProtected(Permissions.Edit, 'revertEditsBy')
    def revertEditsBy(self, username, REQUEST=None):
        """Revert to the latest edit by someone other than username, if any."""
        self.revert(self.revisionBefore(username), REQUEST=REQUEST)

    # restrict this one to managers, it is too powerful for passers-by
    security.declareProtected(Permissions.manage_properties, 'revertEditsEverywhereBy')
    def revertEditsEverywhereBy(self, username, REQUEST=None, batch=0):
        """
        Revert all the most recent edits by username throughout the wiki.
        """
        batch = int(batch)
        n = 0
        for p in self.pageObjects():
            if p.last_editor == username:
                n += 1
                try:
                    p.revertEditsBy(username,REQUEST=REQUEST)
                except IndexError:
                    # IndexError - we don't have a version that old
                    BLATHER('failed to revert edits by %s at %s: %s' \
                            % (username,p.id(),formattedTraceback()))
                if batch and n % batch == 0:
                    BLATHER('committing after %d reverts' % n)
                    get_transaction().commit()
        
    # backwards compatibility / temporary

    def forwardRev(self,rev): return self.revisionCount() - rev - 1

    security.declareProtected(Permissions.View, 'pageRevision')
    def pageRevision(self, rev):
        """
        Get one of the previous revisions of this page object.

        The argument increases to select older revisions, eg revision 1 is
        the most recent version prior to the current one, revision 2 is
        the version before that, etc.
        """
        rev = self.forwardRev(int(rev))
        return self.revisions()[rev]

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


