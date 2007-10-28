"""
Editing methods.
"""

from __future__ import nested_scopes
import re, string, time
from string import split,join,find,lower,rfind,atoi,strip
from urllib import quote, unquote
from types import *
from itertools import *
from email.Message import Message
from copy import deepcopy
import os.path

import ZODB # need this for pychecker
from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import rfc1123_date
from DateTime import DateTime
from Globals import InitializeClass
try:
    from zope.contenttype import guess_content_type
except ImportError:
    try:
        from zope.app.content_types import guess_content_type
    except ImportError:
        from OFS.content_types import guess_content_type
from OFS.DTMLDocument import DTMLDocument
from OFS.ObjectManager import BadRequestException
from OFS.ObjectManager import checkValidId
from zExceptions import BadRequest
import OFS.Image

from pagetypes import PAGETYPES
from Defaults import DISABLE_JAVASCRIPT, LARGE_FILE_SIZE, LEAVE_PLACEHOLDER
import Permissions
from Regexps import javascriptexpr, htmlheaderexpr, htmlfooterexpr
from Utils import get_transaction, BLATHER, parseHeadersBody, safe_hasattr
from I18n import _
from Diff import addedtext, textdiff


class PageEditingSupport:
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
    def checkPermission(self, permission, object):
        return getSecurityManager().checkPermission(permission,object)

    security.declarePublic('createform')      # check permissions at runtime
    def create(self,page=None,text='',type=None,title='',REQUEST=None,log='',
               sendmail=1, parents=None, subtopics=None, pagename=None):
        """Create a new wiki page, and optionally do extra stuff. Normally
        called via edit().

        The page name arguments are confusing. Here's the situation as I
        understand it: XXX cleanup

        - page:     the "original" name of the page we are to create.
        - pagename: an alternate spelling of the above, to ease page 
                    management form implementation. Pass one or the other.
        - title:    optional "new" name to rename to after creation.
                    This allows us to handle the zwiki and CMF/plone
                    edit forms smoothly, supporting rename during creation.

        Page names are assumed to come url-quoted. For the new page id, we use
        a url-safe canonical id derived from the name. (This name and id are
        assumed to be available, or Zwiki would not be calling create.)

        Other arguments:

        - text:      initial content for the new page
        - type:      id of the page type to use (rst, html...)
        - REQUEST:   standard zope argument, pass this to preserve any
                     user authentication. Also, may include file upload
                     data in which case the file is uploaded to the wiki.
        - log:       optional note for edit history and mail-out subject
        - sendmail:  sends mail-out to wiki subscribers, unless disabled
        - parents:   the names of the new page's parent(s), if any
        - subtopics: if non-None, sets the subtopics display property

        Other features:

        - checks the edit_needs_username property as well as permissions
        - redirects to the new page, or to the denied view
        - returns the new page's name, or None
        - if old revisions with this name exist, takes the next revision number
        """
        if not self.checkPermission(Permissions.Add, self.folder()):
            raise 'Unauthorized', (
                _('You are not authorized to add pages in this wiki.'))
        if not self.checkSufficientId(REQUEST):
            if REQUEST: REQUEST.RESPONSE.redirect(self.pageUrl()+'/denied')
            return None
        
        name = unquote(page or pagename)
        id = self.canonicalIdFrom(name)

        # here goes.. sequence is delicate here

        # make a new page object and situate it in the wiki
        # get a hold of it's acquisition wrapper
        p = self.__class__(__name__=id)
        # set title now since manage_afterAdd will use it for wiki outline
        p.title = name
        # place it in the folder
        # newid should be the same as id, but we won't assume
        newid = self.folder()._setObject(id,p)
        p = getattr(self.folder(),newid)
        # check and abort if text is spammy (after name is set up, for logging)
        p.checkForSpam(text)

        p.ensureMyRevisionNumberIsLatest()
        p.setCreator(REQUEST)
        p.setLastEditor(REQUEST)
        p.setLastLog(log)
        p._setOwnership(REQUEST)
        if parents == None: p.parents = [self.pageName()]
        else: p.parents = parents
        self.wikiOutline().add(p.pageName(),p.parents) # update wiki outline

        # choose the specified type, the default type or whatever we're allowed 
        p.setPageType(type or self.defaultPageType())
        p.setText(text,REQUEST)
        p.handleFileUpload(REQUEST)
        p.handleSubtopicsProperty(subtopics,REQUEST)
        if p.autoSubscriptionEnabled(): p.subscribeThisUser(REQUEST)

        # users can alter the page name in the creation form; allow that.
        # We do a full rename, only after all the above, to make sure
        # everything gets handled properly.  We must first commit though,
        # to get p.cb_isMoveable(). Renaming will also get us indexed.
        # We never leave a placeholder, always update backlinks.
        if title and title != p.pageName():
            get_transaction().note('rename during creation')
            get_transaction().commit()
            p.handleRename(title,0,1,REQUEST,log)
        else:
            # we got indexed after _setObject, but do it again with our text
            p.index_object()

        # mail subscribers, unless disabled
        if sendmail:
            p.sendMailToSubscribers(
                p.read(),
                REQUEST=REQUEST,
                subjectSuffix='',
                subject=log,
                message_id=self.messageIdFromTime(p.creationTime())
                )
        # and move on
        if REQUEST:
            try:
                u = (REQUEST.get('redirectURL',None) or
                     REQUEST['URL2']+'/'+ quote(p.id()))
                REQUEST.RESPONSE.redirect(u)
            except KeyError: pass
        return name

    security.declareProtected(Permissions.Comment, 'comment')
    def comment(self, text='', username='', time='',
                note=None, use_heading=None, # not used
                REQUEST=None, subject_heading='', message_id=None,
                in_reply_to=None, exclude_address=None):
        """
        Add a comment to this page.

        We try to do this without unnecessary rendering.  The comment will
        also be mailed out to any subscribers.  If auto-subscription is in
        effect, we subscribe the poster to this page.

        subject_heading is so named to avoid a clash with some existing
        zope subject attribute.  note and use_heading are not used and
        kept only for backwards compatibility.
        """
        if not self.checkSufficientId(REQUEST):
            return self.denied(
                _("Sorry, this wiki doesn't allow anonymous edits. Please configure a username in options first."))

        if self.isDavLocked(): return self.davLockDialog()

        # gather various bits and pieces
        oldtext = self.read()
        if not username:
            username = self.usernameFrom(REQUEST)
            if re.match(r'^(?:\d{1,3}\.){3}\d{1,3}$',username): username = ''
        subject_heading = self.cleanupText(subject_heading)
        text = self.cleanupText(text)
        # some subtleties here: we ensure the page comment and mail-out
        # will use the same message-id, and the same timestamp if possible
        # (helps threading & debugging)
        if time: dtime = DateTime(time)
        else:
            dtime = self.ZopeTime()
            time = dtime.rfc822()
        if not message_id: message_id = self.messageIdFromTime(dtime)

        # make a Message representing this comment
        m = Message()
        m['From'] = username
        m['Date'] = time
        m['Subject'] = subject_heading
        m['Message-ID'] = message_id
        if in_reply_to: m['In-Reply-To'] = in_reply_to
        m.set_payload(text)
        m.set_unixfrom(self.fromLineFrom(m['From'],m['Date'])[:-1])
        
        # discard junk comments
        if not (m['Subject'] or m.get_payload()): return

        # optimisation:
        # add the comment to the page with minimal work - carefully append
        # it to both source and _prerendered cached without re-rendering
        # the whole thing! This might not be legal for all future page
        # types.
        self.saveRevision()
        # add to source, in standard rfc2822 format:
        t = str(m)
        self.checkForSpam(t)
        t = '\n\n' + t
        self.raw += t
        # add to prerendered html:
        # apply single-message prerendering XXX
        t = self.pageType().preRenderMessage(self,m)
        # if it's the first, add appropriate discussion separator
        if self.messageCount()==1:
            t=self.pageType().discussionSeparator(self) + t
        # apply page's standard prerender to the lot XXX
        t = self.pageType().preRender(self,t)
        # and append to the page's prerendered html
        self.setPreRendered(self.preRendered()+t)
        self.cookDtmlIfNeeded()

        self.setLastEditor(REQUEST)
        self.setLastLog(subject_heading)
        if self.autoSubscriptionEnabled(): self.subscribeThisUser(REQUEST)
        self.index_object()

        # send out mail to any subscribers
        # hack the username in there for usernameFrom
        if REQUEST: REQUEST.cookies['zwiki_username'] = m['From']
        self.sendMailToSubscribers(m.get_payload(),
                                   REQUEST,
                                   subject=m['Subject'],
                                   message_id=m['Message-ID'],
                                   in_reply_to=m['In-Reply-To'],
                                   exclude_address=exclude_address
                                   )

        if REQUEST: REQUEST.RESPONSE.redirect(REQUEST['URL1']+'#bottom')

    security.declareProtected(Permissions.Comment, 'append')
    def append(self, text='', separator='\n\n', REQUEST=None, log=''):
        """
        Appends some text to an existing wiki page and scrolls to the bottom.

        Calls edit, may result in mail notifications to subscribers.
        """
        if text:
            if REQUEST: REQUEST.set('redirectURL',REQUEST['URL1']+'#bottom')
            self.edit(text=self.read()+separator+str(text), REQUEST=REQUEST,log=log)

    security.declarePublic('edit')      # check permissions at runtime
    def edit(self, page=None, text=None, type=None, title='', 
             timeStamp=None, REQUEST=None, 
             subjectSuffix='', log='', check_conflict=1, # temp (?)
             leaveplaceholder=LEAVE_PLACEHOLDER, updatebacklinks=1,
             subtopics=None): 
        """
        General-purpose method for editing & creating zwiki pages.

        This method does a lot; combining all this stuff in one powerful
        method simplifies the skin layer above, I think.

        - changes the text and/or formatting type of this (or another )
        page, or creates that page if it doesn't exist.

        - when called from a time-stamped web form, detects and warn when
        two people attempt to work on a page at the same time

        - The username (authenticated user or zwiki_username cookie)
        and ip address are saved in page's last_editor, last_editor_ip
        attributes if a change is made

        - If the text begins with "DeleteMe", delete this page

        - If file has been submitted in REQUEST, create a file or
        image object and link or inline it on the current page.

        - if title differs from page, assume it is the new page name and
        do a rename (the argument remains "title" for backwards
        compatibility)

        - may set, clear or remove this page's show_subtopics property

        - sends mail notification to subscribers if appropriate

        """
        # what are we doing ?
        if page: page = unquote(page)
        if page is None:
            p = self                    # changing this page
        elif self.pageWithNameOrId(page):
            p = self.pageWithNameOrId(page) # changing another page
        else:
            return self.create(page,
                               text or '', # string expected here
                               type,
                               title,
                               REQUEST,
                               log,
                               subtopics=subtopics) # creating a page

        if not self.checkSufficientId(REQUEST):
            return self.denied(
                _("Sorry, this wiki doesn't allow anonymous edits. Please configure a username in options first."))

        if check_conflict:
            if self.checkEditConflict(timeStamp, REQUEST):
                return self.editConflictDialog()
            if self.isDavLocked():
                return self.davLockDialog()

        # ok, changing p. We may do several things at once; each of these
        # handlers checks permissions and does the necessary.
        if p.handleDeleteMe(text,REQUEST,log): return
        p.saveRevision()
        p.handleEditPageType(type,REQUEST,log)
        if text != None: p.handleEditText(text,REQUEST,subjectSuffix,log)
        p.handleSubtopicsProperty(subtopics,REQUEST)
        p.handleFileUpload(REQUEST,log)
        p.handleRename(title,leaveplaceholder,updatebacklinks,REQUEST,log)
        p.index_object()

        # tell browser to reload the page (or redirect elsewhere)
        if REQUEST:
            try:
                REQUEST.RESPONSE.redirect(
                    (REQUEST.get('redirectURL',None) or
                     REQUEST['URL2']+'/'+ quote(p.id())))
            except KeyError: pass

    # This alternate spelling exists so that we can define an "edit" alias
    # in Plone 3, needed to work around a createObject bug
    update = edit

    def handleSubtopicsProperty(self,subtopics,REQUEST=None):
        if subtopics is None: return
        if not self.checkPermission(Permissions.Reparent, self):
            raise 'Unauthorized', (
                _('You are not authorized to reparent or change subtopics links on this ZWiki Page.'))
        subtopics = int(subtopics or '0')
        self.setSubtopicsPropertyStatus(subtopics,REQUEST)

    def handleEditPageType(self,type,REQUEST=None,log=''):
        if not type or type==self.pageTypeId(): return
        if not self.checkPermission(Permissions.ChangeType,self):
            raise 'Unauthorized', (_("You are not authorized to change this ZWiki Page's type."))
        self.setPageType(type)
        self.preRender(clear_cache=1)
        self.setLastEditor(REQUEST)
        self.setLastLog(log)

    security.declarePrivate('setLastLog')
    def setLastLog(self,log):
        """Save an edit log message, if provided."""
        if log and string.strip(log):
            log = string.strip(log)
            get_transaction().note('"%s"' % log)
            self.last_log = log
        else:
            self.last_log = ''

    def lastLog(self):
        """Accessor for this page's last edit log message."""
        return self.last_log

    def handleEditText(self,text,REQUEST=None, subjectSuffix='', log=''):
        old = self.read()
        new = self.cleanupText(text)
        if new == old: return
        if (not
            (self.checkPermission(Permissions.Edit, self) or
             (self.checkPermission(Permissions.Comment, self)
              and find(new,old) == 0))):
            raise 'Unauthorized', (
                _('You are not authorized to edit this ZWiki Page.'))
        self.checkForSpam(addedtext(old, new))
        # do it
        self.setText(text,REQUEST)
        self.setLastEditor(REQUEST)
        self.setLastLog(log)
        self.sendMailToEditSubscribers(
            textdiff(a=old,b=self.read()),
            REQUEST=REQUEST,
            subject='(edit) %s' % log)

    def handleRename(self,newname,leaveplaceholder,updatebacklinks,
                      REQUEST=None,log=''):
        return self.rename(newname, leaveplaceholder=leaveplaceholder,
                           updatebacklinks=updatebacklinks, REQUEST=REQUEST)

    def handleDeleteMe(self,text,REQUEST=None,log=''):
        if not text or not re.match('(?m)^DeleteMe', text):
            return 0
        if not self.checkPermission(Permissions.Edit, self):
            raise 'Unauthorized', (
                _('You are not authorized to edit this ZWiki Page.'))
        if not self.checkPermission(Permissions.Delete, self):
            raise 'Unauthorized', (
                _('You are not authorized to delete this ZWiki Page.'))
        self.setLastLog(log)
        self.delete(REQUEST=REQUEST)
        return 1 # terminate edit processing

    security.declareProtected(Permissions.Delete, 'delete')
    def delete(self,REQUEST=None, pagename=None):
        """Delete this page, after saving a final revision.

        Any subtopics will be reparented. If the pagename argument is
        provided (so named to help the page management form) we will try
        to redirect all incoming wiki links there instead, similar to a
        rename.
        """
        oldname,oldid,redirecturl = self.pageName(),self.getId(),self.upUrl()
        self.reparentChildren(self.primaryParentName())
        if pagename and strip(pagename):
            self._replaceLinksEverywhere(oldname,pagename,REQUEST)
        self.saveRevision()
        self.folder().manage_delObjects([self.getId()])
        self.sendMailToEditSubscribers(
            'This page was deleted.\n',
            REQUEST=REQUEST,
            subjectSuffix='',
            subject='(deleted)')
        if REQUEST: REQUEST.RESPONSE.redirect(redirecturl)

    security.declareProtected(Permissions.Edit, 'revert')
    def revert(self, rev, REQUEST=None):
        """Revert this page to the specified revision's state, updating history.

        We do this by looking at the old page revision object and applying
        a corrective edit to the current page. This records a new page
        revision, reverts text, reverts parents, sends a mailout, etc.
        Last editor, last editor ip, last edit time are updated, cf #1157.

        Page renames are not reverted since the new revisions
        implementation, stand by.
        """
        if not self.checkSufficientId(REQUEST):
            return self.denied(
                _("Sorry, this wiki doesn't allow anonymous edits. Please configure a username in options first."))
        if not rev: return
        rev = int(rev)
        old = self.revision(rev)
        if not old: return
        reparenting = self.getParents() != old.getParents()
        if reparenting and not self.checkPermission(Permissions.Reparent, self):
            raise 'Unauthorized', (
                _('You are not authorized to reparent this ZWiki Page.'))
        # do it
        self.saveRevision()
        self.setText(old.text())
        self.setPageType(old.pageTypeId())
        self.setVotes(old.votes())
        if reparenting:
            self.setParents(old.getParents())
            self.updateWikiOutline()
        self.setLastEditor(REQUEST) #seems better than self.setLastEditorLike(old)
        self.setLastLog('reverted by %s' % self.usernameFrom(REQUEST))
        self.index_object()
        self.sendMailToEditSubscribers(
            'This page was reverted to the %s version.\n' % old.last_edit_time,
            REQUEST=REQUEST,subjectSuffix='',subject='(reverted)')
        if REQUEST is not None: REQUEST.RESPONSE.redirect(self.pageUrl())

    security.declareProtected(Permissions.manage_properties, 'expunge')
    def expunge(self, rev, REQUEST=None):
        """Revert myself to the specified revision, discarding later history."""
        if not rev: return
        rev = int(rev)
        oldrevs = self.oldRevisionNumbers()
        if not rev in oldrevs: return
        id = self.getId()
        def replaceMyselfWith(o): # in zodb (self is not changed)
            self.folder()._delObject(id)
            self.folder()._setObject(id,o)
        def replaceMyselfWithRev(r):
            newself = self.revision(rev)
            newself._setId(id)
            replaceMyselfWith(newself)
        def deleteRevsSince(r):
            for r in oldrevs[oldrevs.index(rev):]:
                self.revisionsFolder()._delObject('%s.%d' % (id,r))
        replaceMyselfWithRev(rev)
        deleteRevsSince(rev)
        BLATHER('expunged %s history after revision %d' % (id,rev))
        if REQUEST is not None: REQUEST.RESPONSE.redirect(self.pageUrl())

    security.declareProtected(Permissions.manage_properties, 'expungeEditsBy')
    def expungeEditsBy(self, username, REQUEST=None):
        """Expunge all my recent edits by username, if any."""
        self.expunge(self.revisionNumberBefore(username), REQUEST=REQUEST)

    security.declareProtected(Permissions.manage_properties, 'expungeEditsEverywhereBy')
    def expungeEditsEverywhereBy(self, username, REQUEST=None, batch=0):
        """Expunge all the most recent edits by username throughout the wiki.

        This is a powerful spam repair tool for managers. It removes all
        recent consecutive edits by username from each page in the
        wiki. The corresponding revisions will disappear from the page
        history.  See #1157.

        Should this use the catalog ? Currently uses a more expensive and
        failsafe brute force ZODB search.
        """
        batch = int(batch)
        for n,p in izip(count(1),
                        [p for p in self.pageObjects() if p.last_editor==username]):
            try:
                p.expungeEditsBy(username,REQUEST=REQUEST)
            except IndexError:
                BLATHER('failed to expunge edits by %s at %s: %s' \
                        % (username,p.id(),formattedTraceback()))
            if batch and (n % batch)==0:
                BLATHER('committing after %d expunges' % n)
                get_transaction().commit()

    security.declareProtected(Permissions.manage_properties, 'expungeLastEditor')
    def expungeLastEditor(self, REQUEST=None):
        """Expunge all the recent edits to this page by the last editor."""
        self.expungeEditsBy(self.last_editor, REQUEST=REQUEST)

    security.declareProtected(Permissions.manage_properties, 'expungeLastEditorEverywhere')
    def expungeLastEditorEverywhere(self, REQUEST=None):
        """Expunge all the recent edits by this page's last editor throughout the wiki."""
        self.expungeEditsEverywhereBy(self.last_editor, REQUEST=REQUEST)

    def ensureTitle(self):
        if not self.title: self.title = self.getId()

    security.declareProtected(Permissions.Rename, 'rename')
    def rename(self,pagename,leaveplaceholder=LEAVE_PLACEHOLDER,
               updatebacklinks=1,sendmail=1,REQUEST=None):
        """Rename this page, if permissions allow. Also ensure name/id
        conformance, keep our children intact, and optionally

        - leave a placeholder page
        - update links to this page throughout the wiki. Warning, this is
          not 100% reliable.
        - notify subscribers. Note the sendmail arg can stop the primary
          creation mailout but not the ones that may result from
          updatebacklinks.
        """
        # figure out what's going on
        oldname, oldid = self.pageName(), self.getId()
        oldnameisfreeform = oldname != oldid
        def clean(s): return re.sub(r'[\r\n]','',s)
        newname = clean(pagename)
        newid = self.canonicalIdFrom(newname)
        namechanged, idchanged = newname != oldname, newid != oldid
        if not newname or not (namechanged or idchanged): return 
        # sequence is important here
        BLATHER('renaming %s (%s) to %s (%s)...'%(oldname,oldid,newname,newid))
        self.ensureTitle()
        if idchanged:
            self.changeIdCarefully(newid)
            if updatebacklinks:
                self._replaceLinksEverywhere(oldid,newid,REQUEST)
        if namechanged:
            self.changeNameCarefully(newname)
            if updatebacklinks and oldnameisfreeform:
                self._replaceLinksEverywhere(oldname,newname,REQUEST)
        self.index_object() # update catalog XXX manage_renameObject may also, if idchanged
        if idchanged and leaveplaceholder: 
            try: self._makePlaceholder(oldid,newname)
            except BadRequestException:
                # special case for CMF/Plone: we'll end up here when first
                # saving a page that was created via the CMS ui - we can't
                # save a placeholder page since the canonical ID hasn't
                # really changed
                pass
        if namechanged and sendmail:
            self._sendRenameNotification(oldname,newname,REQUEST)
        BLATHER('rename complete')
        if REQUEST: REQUEST.RESPONSE.redirect(self.pageUrl())

    def _makePlaceholder(self,oldid,newname): 
        self.create(
            oldid,
            _("This page was renamed to %s. You can delete this one if no longer needed.\n") % (newname),
            sendmail=0)

    def _sendRenameNotification(self,oldname,newname,REQUEST):
        self.sendMailToEditSubscribers(
            'This page was renamed from %s to %s.\n'%(oldname,newname),
            REQUEST=REQUEST,
            subjectSuffix='',
            subject='(renamed)')

    def changeNameCarefully(self,newname):
        """Change this page's name, preserving important info."""
        self.reparentChildren(newname)
        self.wikiOutline().replace(self.pageName(),newname)
        self.title = newname

    def changeIdCarefully(self,newid):
        """Change this page's id, preserving important info."""
        # this object will be replaced with another
        creation_time, creator, creator_ip = \
          self.creation_time, self.creator, self.creator_ip
        # manage_after* has the effect of losing our place in the hierarchy
        parentmap = deepcopy(self.wikiOutline().parentmap())
        childmap = deepcopy(self.wikiOutline().childmap())
        self.folder().manage_renameObject(self.getId(),newid)
        self.creation_time, self.creator, self.creator_ip = \
          creation_time, creator, creator_ip
        self.wikiOutline().setParentmap(parentmap)
        self.wikiOutline().setChildmap(childmap)
        self.ensureMyRevisionNumberIsLatest()

    def reparentChildren(self,newparent):
        children = self.childrenIdsAsList()
        if children:
            BLATHER('reparenting children of',self.getId())
            for id in children:
                child = getattr(self.folder(),id) # XXX poor caching
                child.removeParent(self.pageName())
                child.addParent(newparent)
                child.index_object() # XXX need only reindex parents
                
    def _replaceLinksEverywhere(self,oldlink,newlink,REQUEST=None):
        """Replace one link with another throughout the wiki.

        Freeform links should not be enclosed in brackets.
        Comes with an appropriately big scary-sounding name. See
        _replaceLinks for more.
        """
        BLATHER('replacing all %s links with %s' % (oldlink,newlink))
        for p in self.backlinksFor(oldlink):
            # this is an extensive, risky operation which can fail for
            # a number of reasons - carry on regardless so we don't
            # block renames
            # poor caching
            try: p.getObject()._replaceLinks(oldlink,newlink,REQUEST)
            except:
                BLATHER('_replaceLinks failed to update %s links in %s' \
                     % (oldlink,p.id))

    def _replaceLinks(self,oldlink,newlink,REQUEST=None):
        """Replace occurrences of oldlink with newlink in my text.

        Freeform links should not be enclosed in brackets.
        We'll also replace bare wiki links to a freeform page's id,
        but not fuzzy links.
        This tries not to do too much damage, but is pretty dumb.
        Maybe it should use the pre-linking information.
        It's slow, since it re-renders every page it changes.
        """
        if self.isWikiName(oldlink):
            # add a \b to wikinames to make matches more accurate
            oldpat = r'\b%s\b' % oldlink
        else:
            # replace both the freeform  and the equivalent bare wiki link
            # XXX assumes single brackets are allowed in this wiki
            oldpat = r'(\[%s\]|\b%s\b)' \
                     % (re.escape(oldlink), self.canonicalIdFrom(oldlink))
        newpat = (self.isWikiName(newlink) and newlink) or '[%s]' % newlink
        self.edit(text=re.sub(oldpat, newpat, self.read()),
                  REQUEST=REQUEST)

    def folderContains(self,folder,id):
        """check folder contents safely, without acquiring"""
        return safe_hasattr(folder.aq_base,id)

    def uploadFolder(self):
        """Where to store uploaded files (an 'uploads' subfolder if
        present, otherwise the wiki folder)."""
        f = self.folder()
        if (self.folderContains(f,'uploads') and f.uploads.isPrincipiaFolderish):
            f = f.uploads
        return f

    def checkUploadPermissions(self):
        """Raise an exception if the current user does not have permission
        to upload to this wiki page."""
        if not (self.checkPermission(Permissions.Upload,self.uploadFolder())):
            raise 'Unauthorized', (_('You are not authorized to upload files here.'))
        if not (self.checkPermission(Permissions.Edit, self) or
                self.checkPermission(Permissions.Comment, self)):
            raise 'Unauthorized', (_('You are not authorized to add a link on this ZWiki Page.'))

    def requestHasFile(self,r):
        return (r and safe_hasattr(r,'file') and safe_hasattr(r.file,'filename') and r.file.filename)

    def _sendUploadNotification(self,newid,REQUEST):
        self.sendMailToEditSubscribers(
            'Uploaded file "%s" on page "%s".\n' % (newid,self.pageName()),
            REQUEST=REQUEST,
            subjectSuffix='',
            subject='(upload)')

    def handleFileUpload(self,REQUEST,log=''):
        if not self.requestHasFile(REQUEST): return
        self.checkUploadPermissions()
        newid = self._addFileFromRequest(REQUEST,log=log)
        if not newid: raise 'Error', (_('Sorry, file creation failed for some reason.'))
        self._sendUploadNotification(newid,REQUEST)

    def _addFileFromRequest(self,REQUEST,log=''):
        """Add and link a new File or Image object, depending on file's filename
        suffix. Returns a tuple containing the new id, content type &
        size, or (None,None,None).
        """
        # ensure we have a suitable file, id and title
        file, title = REQUEST.file, str(REQUEST.get('title',''))
        id, title = OFS.Image.cookId('', title, file)
        if not id: return None
        folder = self.uploadFolder()
        try: checkValidId(folder,id,allow_dup=1)
        except BadRequest:
            id, ext = os.path.splitext(id)
            id = self.canonicalIdFrom(id)
            id = id + ext
        # create the file or image object, unless it already exists
        # XXX should use CMF/Plone content types when appropriate
        if not (self.folderContains(folder,id) and
                folder[id].meta_type in ('File','Image')): #'Portal File','Portal Image')):
            if guess_content_type(file.filename)[0][0:5] == 'image':
#                 if self.inCMF():
#                     #from Products.ATContentTypes import ATFile, ATImage
#                     #folder.create(ATImage) ...
#                 else:
                id = folder._setObject(id, OFS.Image.Image(id,title,''))
            else:
#                 if self.inCMF():
#                 else:
                id = folder._setObject(id, OFS.Image.File(id,title,''))
        # adding the data after creation is more efficient, reportedly
        ob = folder._getOb(id)
        ob.manage_upload(file)
        # and link/inline it
        self._addFileOrImageToPage(id,ob.content_type,ob.getSize(),log,REQUEST)
        return id

    def _addFileOrImageToPage(self, id, content_type, size, log, REQUEST):
        """Add a file link or image to this page, unless it's already
        there.  Inline images which are not too big.
        """
        alreadythere = re.search(r'(src|href)="%s"' % id,self.text())
        if alreadythere: return
        def fileOrImageLink():
            folderurl = self.uploadFolder().absolute_url()
            shouldinline = (
                (content_type.startswith('image')
                 and not (safe_hasattr(REQUEST,'dontinline') and REQUEST.dontinline)
                 and size <= LARGE_FILE_SIZE))
            if shouldinline:
                return self.pageType().inlineImage(self,id,folderurl+'/'+id)
            else:
                return self.pageType().linkFile(self,id,folderurl+'/'+id)
        def appendQuietly(linktxt,log,REQUEST):
            self.setText(self.read()+linktxt,REQUEST)
            self.setLastEditor(REQUEST)
            self.setLastLog(log)
            self.index_object()
        appendQuietly(fileOrImageLink(),log,REQUEST)
        
    def _setOwnership(self, REQUEST=None):
        """Set appropriate ownership for a new page.  To help control
        executable content, we make sure the new page acquires it's owner
        from the parent folder.
        """
        self._deleteOwnershipAfterAdd()
            
    # for IssueNo0157
    _old_read = DTMLDocument.read
    security.declareProtected(Permissions.View, 'read')
    def read(self):
        return re.sub('<!--antidecapitationkludge-->\n\n?','',
                      self._old_read())

    security.declareProtected(Permissions.View, 'text')
    def text(self, REQUEST=None, RESPONSE=None):
        """
        Return this page's source text, with text/plain content type.
        
        (a permission-free version of document_src)
        # XXX security ?
        """
        if RESPONSE is not None:
            RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')
            #RESPONSE.setHeader('Last-Modified', rfc1123_date(self._p_mtime))
        return self.read()

    def setText(self, text='', REQUEST=None):
        """
        Change this page's text.

        Does cleanups and triggers pre-rendering and DTML re-parsing.
        """
        self.raw = self.cleanupText(text)
        self.preRender(clear_cache=1)
        # re-cook DTML's cached parse data if necessary
        # will prevent edit if DTML can't parse.. hopefully no auth trouble
        self.cookDtmlIfNeeded()
        # try running the DTML, to prevent edits if DTML can't execute
        # got authorization problems, commit didn't help..
        #if self.supportsDtml() and self.dtmlAllowed():
        #    #get_transaction().commit()
        #    DTMLDocument.__call__(self,self,REQUEST,REQUEST.RESPONSE)

    def checkForSpam(self, t):
        """
        Check for signs of spam in some text, and raise an error if found.

        Also looks at the current user's info in REQUEST.
        """
        REQUEST = getattr(self,'REQUEST',None)
        username = self.usernameFrom(REQUEST,ip_address=0)
        ip = getattr(REQUEST,'REMOTE_ADDR','')
        page = self.pageName()
        def raiseSpamError(reason, verbose_reason):
            BLATHER(('blocked edit from %s (%s) on %s (%s)\n%s\n') % \
                    (ip, username, page, reason, t))
            raise _("There was a problem: %s" % \
                    (verbose_reason))
            
        # banned link pattern ?
        for pat in getattr(self.folder(),'banned_links',[]):
            pat = strip(pat)
            if pat and re.search(pat,t):
                raiseSpamError(_("banned_links match"),
                               _("your edit contained a banned link pattern. Please contact the site administrator for help."))

        # anonymous edit with too many external links ?
        # tries to count the links added by this edit.
        prop = 'max_anonymous_links'
        if (not self.requestHasUsername(REQUEST) and
            safe_hasattr(self.folder(), prop)):
            try: max = int(getattr(self.folder(), prop))
            except ValueError: max = None
            if max is not None:
                if len(re.findall(r'https?://',t)) > max:
                    raiseSpamError(_("exceeded max_anonymous_links"),
                                   _("adding of external links by unidentified users is restricted. Please back up and remove some of the http urls you added, or contact the site administrator for help."))

        # and a similar check for identified users
        # XXX simplify ? one property for both ?
        prop = 'max_identified_links'
        # we'll handle either an int or string property
        if (safe_hasattr(self.folder(), prop)):
            try: max = int(getattr(self.folder(), prop))
            except ValueError: max = None
            if max is not None:
                if len(re.findall(r'https?://',t)) > max:
                    raiseSpamError(_("exceeded max_identified_links"),
                                   _("adding of external links is restricted, even for identified users. Please back up and remove some of the http urls you added, or contact the site administrator for help."))

    def cleanupText(self, t):
        """Clean up incoming text and make sure that it's utf8-encoded."""
        def checkutf8(s): unicode(t,'utf-8')
        def stripcr(t): return re.sub('\r\n','\n',t)
        def disablejs(t): return re.sub(javascriptexpr,r'&lt;disabled \1&gt;',t)
        checkutf8(t)
        return disablejs(stripcr(t))

    def setLastEditor(self, REQUEST=None):
        """Record last editor info based on the current REQUEST and time."""
        if REQUEST:
            self.last_editor_ip = REQUEST.REMOTE_ADDR
            self.last_editor = self.usernameFrom(REQUEST)
        else:
            # this has been fiddled with before
            # if we have no REQUEST, at least update last editor
            self.last_editor_ip = ''
            self.last_editor = ''
        self.last_edit_time = DateTime().ISO8601()

    def setLastEditorLike(self,p):
        """Copy last editor info from p."""
        self.last_editor    = p.last_editor
        self.last_editor_ip = p.last_editor_ip
        self.last_edit_time = p.last_edit_time

    def hasCreatorInfo(self):
        """True if this page already has creator attributes."""
        return (safe_hasattr(self,'creator') and
                safe_hasattr(self,'creation_time') and
                safe_hasattr(self,'creator_ip'))

    def setCreator(self, REQUEST=None):
        """Record my creator, creator_ip & creation_time."""
        self.creation_time = DateTime().ISO8601()
        if REQUEST:
            self.creator_ip = REQUEST.REMOTE_ADDR
            self.creator = self.usernameFrom(REQUEST)
        else:
            self.creator_ip = ''
            self.creator = ''

    def setCreatorLike(self,p):
        """Copy creator info from p."""
        self.creator       = p.creator
        self.creator_ip    = p.creator_ip
        self.creation_time = p.creation_time

    security.declareProtected(Permissions.View, 'checkEditConflict')
    def checkEditConflict(self, timeStamp, REQUEST):
        """
        Warn if this edit would be in conflict with another.

        Edit conflict checking based on timestamps -
        
        things to consider: what if
        - we are behind a proxy so all ip's are the same ?
        - several people use the same cookie-based username ?
        - people use the same cookie-name as an existing member name ?
        - no-one is using usernames ?

        strategies:
        0. no conflict checking

        1. strict - require a matching timestamp. Safest but obstructs a
        user trying to backtrack & re-edit. This was the behaviour of
        early zwiki versions.

        2. semi-careful - record username & ip address with the timestamp,
        require a matching timestamp or matching non-anonymous username
        and ip.  There will be no conflict checking amongst users with the
        same username (authenticated or cookie) connecting via proxy.
        Anonymous users will experience strict checking until they
        configure a username.

        3. relaxed - require a matching timestamp or a matching, possibly
        anonymous, username and ip. There will be no conflict checking
        amongst anonymous users connecting via proxy. This is the current
        behaviour.
        """
        username = self.usernameFrom(REQUEST)
        if (timeStamp is not None and
            timeStamp != self.timeStamp() and
            (not safe_hasattr(self,'last_editor') or
             not safe_hasattr(self,'last_editor_ip') or
             username != self.last_editor or
             REQUEST.REMOTE_ADDR != self.last_editor_ip)):
            return 1
        else:
            return 0

    security.declareProtected(Permissions.View, 'timeStamp')
    def timeStamp(self):
        return str(self._p_mtime)
    
    security.declareProtected(Permissions.FTP, 'manage_FTPget')
    def manage_FTPget(self):
        """
        Get source for FTP download.
        """
        #candidates = list(self.allowedPageTypes())
        #types = "%s (alternatives:" % self.pageTypeId()
        #if self.pageTypeId() in candidates:
        #    candidates.remove(self.pageTypeId())
        #for i in candidates:
        #    types = types + " %s" % i
        #types = types + ")"
        types = "%s" % self.pageTypeId()
        return "Wiki-Safetybelt: %s\nType: %s\nLog: \n\n%s" % (
            self.timeStamp(), types, self.read())

    security.declarePublic('isDavLocked')
    def isDavLocked(self):
        return safe_hasattr(self,'wl_isLocked') and self.wl_isLocked()

    security.declareProtected(Permissions.Edit, 'PUT')
    def PUT(self, REQUEST, RESPONSE):
        """Handle HTTP/FTP/WebDav PUT requests."""
        self.dav__init(REQUEST, RESPONSE)
        self.dav__simpleifhandler(REQUEST, RESPONSE, refresh=1)
        self._validateProxy(REQUEST)
        body = REQUEST.get('BODY', '')
        headers, body = parseHeadersBody(body)
        log = string.strip(headers.get('Log', headers.get('log', ''))) or ''
        type = string.strip(headers.get('Type', headers.get('type', ''))) or None
        if type is not None: type = string.split(type)[0]
        timestamp = string.strip(headers.get('Wiki-Safetybelt', '')) or None
        if timestamp and self.checkEditConflict(timestamp, REQUEST):
            RESPONSE.setStatus(423) # Resource Locked
            return RESPONSE
        try:
            self.edit(text=body, type=type, timeStamp=timestamp,
                      REQUEST=REQUEST, log=log, check_conflict=0)
        except 'Unauthorized':
            RESPONSE.setStatus(401)
            return RESPONSE
        RESPONSE.setStatus(204)
        return RESPONSE

    security.declareProtected(Permissions.Edit, 'manage_edit')
    def manage_edit(self, data, title, REQUEST=None):
        """Do standard manage_edit kind of stuff, using our edit."""
        #self.edit(text=data, title=title, REQUEST=REQUEST, check_conflict=0)
        #I think we need to bypass edit to provide correct permissions
        self.title = title
        self.setText(data,REQUEST)
        self.setLastEditor(REQUEST)
        self.reindex_object()
        if REQUEST:
            message="Content changed."
            return self.manage_main(self,REQUEST,manage_tabs_message=message)

    def allowedPageTypes(self):
        """
        List the page type ids which may be selected in this wiki's edit form.

        This will be all available page types, unless overridden by an
        allowed_page_types property.
        """
        return (filter(lambda x:strip(x),getattr(self,'allowed_page_types',[]))
                or map(lambda x:x._id, PAGETYPES))

    def defaultPageType(self):
        """This wiki's default page type."""
        return self.allowedPageTypes()[0]

    security.declareProtected(Permissions.Add, 'split')
    def split(self):
        """
        Move this page's major sections to sub-pages, if supported.

        Delegates to the page type; at present only the restructured
        text page type does this.

        Watch out for confusion with string.split which might arise
        here and there.
        """
        return self.pageType().split(self)
    
    security.declareProtected(Permissions.Delete, 'merge')
    def merge(self):
        """
        Merge sub-pages as sections of this page, if supported.

        Delegates to the page type; at present only the restructured
        text page type does this.
        """
        return self.pageType().merge(self)
    
InitializeClass(PageEditingSupport)

