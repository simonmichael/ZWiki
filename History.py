"""
Permanent revision history for zwiki pages.

Warning: this implementation might be zodb-cache-unfriendly as revisions
increase.
"""

from AccessControl import getSecurityManager, ClassSecurityInfo
from AccessControl.class_init import InitializeClass
try:    from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2 as Folder
except ImportError: from OFS.Folder import Folder # zope 2.7
from Utils import safe_hasattr, sorted, registerSupportFolderId

import re
import Permissions
from OutlineSupport import PersistentOutline

REVISIONS_FOLDER_ID = 'revisions'
registerSupportFolderId(REVISIONS_FOLDER_ID)

class PageHistorySupport:
    """
    This mixin provides methods to save, browse and restore zwiki page
    revisions.  Unlike zope's built-in transaction history, these are
    saved forever, as page objects in a revisions subfolder.  Individual
    revisions may be deleted manually without ill effect.

    The methods below should generally work whether they are called on the
    latest revision (in the wiki folder), or on an older revision (in the
    revisions subfolder), except where noted.
    """
    security = ClassSecurityInfo()

    def ensureRevisionsFolder(self):
        if self.revisionsFolder() is None:
            self.folder()._setObject(REVISIONS_FOLDER_ID,Folder(REVISIONS_FOLDER_ID))

    def inRevisionsFolder(self):
        return self.folder().getId() == REVISIONS_FOLDER_ID

    def revisionsFolder(self):
        """Get the revisions subfolder, even called from within it, or
        None if it does not exist yet."""
        if self.inRevisionsFolder():
            return self.folder()
        elif safe_hasattr(self.folder().aq_base, REVISIONS_FOLDER_ID):
            f = self.folder()[REVISIONS_FOLDER_ID]
            if f.isPrincipiaFolderish:
                return f
        return None
            
    security.declareProtected(Permissions.View, 'revisions')
    def revisions(self):
        """
        Get a list of this page's revisions, oldest first.
        
        A page's revisions are all the page objects with the same root id
        plus a possible dot-number suffix. The one with no suffix is the
        latest revision, kept in the main wiki folder; older revisions
        have a suffix and are kept in the revisions subfolder.
        """
        return self.oldRevisions() + [self.latestRevision()]

    def latestRevision(self):
        if self.inRevisionsFolder(): f = self.wikiFolder()
        else: f = self.folder()
        return f[self.getIdBase()]

    def oldRevisionIds(self):
        f = self.revisionsFolder()
        if not f:
            return []
        else:
            isrev = re.compile(r'%s\.\d+$' % self.getIdBase()).match
            ids = filter(isrev, list(f.objectIds(spec=self.meta_type)))
            # probably in the right order, but let's make sure
            ids.sort(lambda a,b: cmp(int(a.split('.')[1]), int(b.split('.')[1])))
            return ids

    def oldRevisions(self):
        return [self.revisionsFolder()[id] for id in self.oldRevisionIds()]

    def getIdBase(self):
        """This page's id with any revision number suffix removed."""
        return re.sub(r'^(.*)\.\d+$', r'\1', self.getId())

    security.declareProtected(Permissions.View, 'revisionCount')
    def revisionCount(self):
        """The number of revisions existing for this page."""
        return len(self.revisions())

    security.declareProtected(Permissions.View, 'revision')
    def revision(self, rev):
        """Get the specified revision of this page object (starting from 1)."""
        if rev:
            # should be no more than one, but you never know
            revs = [r for r in self.revisions() if r.revisionNumber()==rev]
            if revs: return revs[0]
        return None

    security.declareProtected(Permissions.View, 'previousRevision')
    def previousRevision(self):
        """Get the oldest saved revision of this page previous to this one."""
        r = self.previousRevisionNumber()
        if r: return self.revision(r)
        else: return None

    security.declareProtected(Permissions.View, 'nextRevision')
    def nextRevision(self):
        """Get the next saved revision of this page after this one."""
        r = self.nextRevisionNumber()
        if r: return self.revision(r)
        else: return None

    security.declareProtected(Permissions.View, 'revisionNumber')
    def revisionNumber(self):
        """Get this page's revision number."""
        return getattr(self.aq_base,'revision_number',1)

    def revisionNumberFromId(self):
        m = re.search(r'\.(\d+)$',self.getId())
        if m: return int(m.group(1))
        else: return None

    def revisionNumbers(self):
        """The revision numbers of all available revisions of this page
        (sorted)."""
        return sorted([r.revisionNumber() for r in self.revisions()])

    def oldRevisionNumbers(self):
        """The revision numbers of all old revisions, excluding the latest
        one (sorted)."""
        return sorted([r.revisionNumber() for r in self.oldRevisions()])

    def firstRevisionNumber(self):
        """The revision number of the earliest saved revision of this page."""
        return self.revisionNumbers()[0]

    def lastRevisionNumber(self):
        """The revision number of the latest saved revision of this page."""
        return self.revisionNumbers()[-1]

    def previousRevisionNumber(self):
        """The number of the latest saved revision before this one, or None."""
        revnos = self.revisionNumbers()
        i = revnos.index(self.revisionNumber())
        if i: return revnos[i-1]
        else: return None

    def nextRevisionNumber(self):
        """The number of the next saved revision after this one, or None."""
        revnos = self.revisionNumbers()
        i = revnos.index(self.revisionNumber())
        if i < len(revnos)-1: return revnos[i+1]
        else: return None

    def revisionNumberBefore(self, username): # -> revision number | none
        # depends on: self, revisions
        """The revision number of the last edit not by username, or None."""
        for r in range(self.revisionCount(),0,-1):
            if self.revision(r).lastEditor() != username:
                return r
        return None

    def ensureMyRevisionNumberIsLatest(self):
        """Make sure this page's revision number is larger than that of
        any existing revisions. Don't bother updating catalog."""
        oldrevs = self.oldRevisionNumbers()
        r = oldrevs and (oldrevs[-1] + 1) or 1
        if self.revisionNumber() != r: self.revision_number = r

    def saveRevision(self, REQUEST=None):
        """Save a copy of this page as a new revision in the revisions
        folder and increment its revision number.  This has no effect if
        called on a revision object, or a non-ZODB object (such as a
        temporary page object created by plone's portal_factory).

        NB normally the revision number just increments by 1, but if there
        is already a revision object with that number (which can happen
        from renaming, eg), we first bump this page's revision number to
        the number after all existing revisions.
        """
        def inPortalFactory(self):
            return self.inCMF() and self.folder().getId() == 'portal_factory'
        if self.inRevisionsFolder() or inPortalFactory(self): return
        self.ensureRevisionsFolder()
        self.ensureMyRevisionNumberIsLatest()
        rid = '%s.%d' % (self.getId(), self.revisionNumber())
        ob = self._getCopy(self.folder())
        ob._setId(rid)

        # kludge so the following won't update an outline cache
        # in the revisions folder (hopefully thread-safe, otherwise
        # escalate to "horrible kludge"): XXX how to test ?
        manage_afterAdd                = self.__class__.manage_afterAdd
        wikiOutline                    = self.__class__.wikiOutline
        self.__class__.manage_afterAdd = lambda self,item,container:None
        self.__class__.wikiOutline     = lambda self:PersistentOutline()

        self.revisionsFolder()._setObject(rid, ob)

        # clean up after kludge
        self.__class__.manage_afterAdd = manage_afterAdd
        self.__class__.wikiOutline     = wikiOutline

        # and increment
        self.revision_number = self.revisionNumber() + 1

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


