######################################################################
# editing methods

from __future__ import nested_scopes
import re, string, time
from string import split,join,find,lower,rfind,atoi,strip
from urllib import quote, unquote
from types import *

import ZODB # need this for pychecker
from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import rfc1123_date
from DateTime import DateTime
import Globals
from OFS.content_types import guess_content_type
from OFS.DTMLDocument import DTMLDocument
from OFS.ObjectManager import BadRequestException
import OFS.Image

from Defaults import DISABLE_JAVASCRIPT, LARGE_FILE_SIZE, \
     ALLOWED_PAGE_TYPES, ALLOWED_PAGE_TYPES_IN_PLONE, LEAVE_PLACEHOLDER
import Permissions
from Regexps import javascriptexpr, htmlheaderexpr, htmlfooterexpr
from Utils import BLATHER, parseHeadersBody
from LocalizerSupport import LocalDTMLFile, _, N_
DTMLFile = LocalDTMLFile
del LocalDTMLFile


class EditingSupport:
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
    def checkPermission(self, permission, object):
        return getSecurityManager().checkPermission(permission,object)

# XXX refactor

    security.declareProtected(Permissions.View, 'create') 
    # really Permissions.Add, but keep our informative unauthorized message
    def create(self,page,text=None,type=None,title='',REQUEST=None,log='',
               leaveplaceholder=1, updatebacklinks=1, sendmail=1,
               subtopics=None):
        """
        Create a new wiki page and redirect there if appropriate; can
        upload a file at the same time.  Normally edit() will call
        this for you.

        Assumes page has been url-quoted. If it's not a url-safe name, we
        will create the page with a url-safe id that's similar. We assume
        this id won't match anything already existing (zwiki would have
        linked it instead of offering to create it).

        Can handle a rename during page creation also. This seems less
        sensible than in edit(), but it helps support CMF/Plone.
        """
        # do we have permission ?
        if not self.checkPermission(Permissions.Add,self.folder()):
            raise 'Unauthorized', (
                _('You are not authorized to add ZWiki Pages here.'))

        name = unquote(page)
        id = self.canonicalIdFrom(name)

        # make a new (blank) page object, situate it
        # in the parent folder and get a hold of it's
        # normal acquisition wrapper
        p = self.__class__(source_string='', __name__=id)
        # make sure the title is set, since manage_afterAdd
        # will use it to make an entry in the wiki outline
        p.title = name
        # newid should be the same as id, but don't assume
        newid = self.folder()._setObject(id,p)
        p = getattr(self.folder(),newid)

        p.setCreator(REQUEST)
        p.setLastEditor(REQUEST)
        p.setLastLog(log)
        p._setOwnership(REQUEST)
        p.parents = [self.title_or_id()]
        self.wikiOutline().add(p.pageName(),p.parents) # update wiki outline

        # set the specified page type, otherwise use this wiki's default
        p.setPageType(type)

        # set initial page text as edit() would, with cleanups and dtml
        # validation
        p.setText(text or '',REQUEST)

        # if a file was submitted as well, handle that
        p.handleFileUpload(REQUEST)

        # if a subtopics property was specified, handle that
        p.handleSubtopicsProperty(subtopics,REQUEST)

        # plone support, etc: they might alter the page name in the
        # creation form! allow that. We do a full rename after all the
        # above to make sure everything gets handled properly.  We need to
        # commit first though, so p.cb_isMoveable() succeeds.
        # Renaming will do all the indexing we need.
        if title and title != p.title_or_id():
            get_transaction().note('rename during creation')
            get_transaction().commit()
            p.handleRename(title,leaveplaceholder,updatebacklinks,REQUEST,log)
        else:
            # we got indexed after _setObject,
            # but do it again with our text in place
            p.index_object()

        #if p.usingRegulations():
        #    # initialize regulations settings.
        #    p.setRegulations(REQUEST,new=1)

        # if auto-subscription is enabled (folder-wide), subscribe the creator
        if p.autoSubscriptionEnabled():
           usernameoremail = (REQUEST and (
                              str(REQUEST.get('AUTHENTICATED_USER')) or
                              REQUEST.cookies.get('email')))
           if usernameoremail:
               if not self.isWikiSubscriber(usernameoremail):
                   p.subscribe(usernameoremail)
                   BLATHER('auto-subscribing',usernameoremail,'to',p.id())

        # always mail out page creations, unless disabled
        # and give these a message id we can use for threading
        message_id = self.messageIdFromTime(p.creationTime())
        if sendmail:
            p.sendMailToSubscribers(p.read(),
                                    REQUEST=REQUEST,
                                    subjectSuffix='',
                                    subject='(new) '+log,
                                    message_id=message_id)

        # redirect browser if needed
        if REQUEST is not None:
            try:
                u = (REQUEST.get('redirectURL',None) or
                     REQUEST['URL2']+'/'+ quote(p.id()))
                REQUEST.RESPONSE.redirect(u)
            except KeyError:
                pass

    security.declarePublic('isDavLocked')
    def isDavLocked(self):
        return hasattr(self,'wl_isLocked') and self.wl_isLocked()

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
        if self.isDavLocked(): return self.davLockDialog()

        # gather various bits and pieces
        oldtext = self.read()
        if not username:
            username = self.usernameFrom(REQUEST)
            if re.match(r'^[0-9\.\s]*$',username): username = ''
        # some subtleties here: we ensure the page comment and mail-out
        # will use the same message-id, and the same timestamp if possible
        # (helps threading & debugging)
        if time: dtime = DateTime(time)
        else:
            dtime = self.ZopeTime()
            time = dtime.rfc822()
        if not message_id: message_id = self.messageIdFromTime(dtime)

        # make a Message representing this comment
        import email.Message
        m = email.Message.Message()
        m['From'] = username
        m['Date'] = time
        m['Subject'] = subject_heading
        m['Message-ID'] = message_id
        if in_reply_to: m['In-Reply-To'] = in_reply_to
        m.set_payload(self._cleanupText(text))
        m.set_unixfrom(self.fromLineFrom(m['From'],m['Date'])[:-1])
        
        # discard junk comments
        if not (m['Subject'] or m.get_payload()): return

        # add the comment to the page with minimal work - carefully append
        # it to both source and _prerendered cached without re-rendering
        # the whole thing! This might not be legal for all future page
        # types.
        # add to source, in standard rfc2822 format:
        t = str(m)
        if self.usingPurpleNumbers(): t = self.addPurpleNumbersTo(t,self)
        t = '\n\n' + t
        self.raw += t
        # add to html cache, rendered:
        t = self.pageType().preRenderMessage(self,m)
        if self.messageCount()==1:t=self.pageType().discussionSeparator(self)+t
        t = self.pageType().preRender(self,t)
        self.setPreRendered(self.preRendered()+t)
        self.cookDtmlIfNeeded()

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

        if self.autoSubscriptionEnabled(): self.subscribeThisUser(REQUEST)
        self.setLastEditor(REQUEST)
        self.setLastLog(note)
        self.updateCatalog()
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
             leaveplaceholder=1, updatebacklinks=1,
             subtopics=None): 
        """
        General-purpose method for editing & creating zwiki pages.

        Changes the text and/or markup type of this (or the specified)
        page, or creates the specified page (name or id allowed) if it
        does not exist.
        
        Other special features:

        - Usually called from a time-stamped web form; we use
        timeStamp to detect and warn when two people attempt to work
        on a page at the same time. This makes sense only if timeStamp
        came from an editform for the page we are actually changing.

        - The username (authenticated user or zwiki_username cookie)
        and ip address are saved in page's last_editor, last_editor_ip
        attributes if a change is made

        - If the text begins with "DeleteMe", move this page to the
        recycle_bin subfolder.

        - If file has been submitted in REQUEST, create a file or
        image object and link or inline it on the current page.

        - May also cause mail notifications to be sent to subscribers

        - if title differs from page, assume it is the new page name and
        do a rename (the argument remains as "title" for backwards
        compatibility)

        - may set, clear or remove this page's show_subtopics property

        This code has become more complex to support late page
        creation, but the api should now be more general & powerful
        than it was.  Doing all this stuff in one method simplifies
        the layer above (the skin) I think.
        """
        #self._validateProxy(REQUEST)   # XXX correct ? don't think so
                                        # do zwiki pages obey proxy roles ?

        if page: page = unquote(page)
        # are we changing this page ?
        if page is None:
            p = self
        # changing another page ?
        elif self.pageWithNameOrId(page):
            p = self.pageWithNameOrId(page)
        # or creating a new page
        else:
            return self.create(page,text,type,title,REQUEST,log,
                               subtopics=subtopics)

        # ok, changing p. We may be doing several things here;
        # each of these handlers checks permissions and does the
        # necessary. Some of these can halt further processing.
        # todo: tie these in to mail notification, along with 
        # other changes like reparenting
        if check_conflict and self.checkEditConflict(timeStamp, REQUEST):
            return self.editConflictDialog()
        if check_conflict and hasattr(self,'wl_isLocked') and self.wl_isLocked():
            return self.davLockDialog()
        if p.handleDeleteMe(text,REQUEST,log): return
        p.handleEditPageType(type,REQUEST,log)
        p.handleEditText(text,REQUEST,subjectSuffix,log)
        p.handleSubtopicsProperty(subtopics,REQUEST)
        p.handleFileUpload(REQUEST,log)
        p.handleRename(title,leaveplaceholder,updatebacklinks,REQUEST,log)
        #if self.usingRegulations(): p.handleSetRegulations(REQUEST)
        p.updateCatalog()
        # tell browser to reload the page
        if REQUEST:
            try:
                u = (REQUEST.get('redirectURL',None) or
                     REQUEST['URL2']+'/'+ quote(p.id()))
                REQUEST.RESPONSE.redirect(u)
            except KeyError: pass

    def handleSubtopicsProperty(self,subtopics,REQUEST=None):
        if subtopics is not None:
            # do we have permission ?
            if not self.checkPermission(Permissions.Reparent, self):
                raise 'Unauthorized', (
                    _('You are not authorized to reparent or change subtopics links on this ZWiki Page.'))
            subtopics = int(subtopics or '0')
            self.setSubtopicsPropertyStatus(subtopics,REQUEST)

    # see Regulations.py
    #def handleSetRegulations(self,REQUEST):
    #    if REQUEST.get('who_owns_subs',None) != None:
    #        # do we have permission ?
    #        if not self.checkPermission(Permissions.ChangeRegs,self):
    #            raise 'Unauthorized', (
    #              _("You are not authorized to set this ZWiki Page's regulations."))
    #        self.setRegulations(REQUEST)
    #        self.preRender(clear_cache=1)
    #        #self.setLastEditor(REQUEST)

    def handleEditPageType(self,type,REQUEST=None,log=''):
        # is the new page type valid and different ?
        if (type is not None and
            type != self.pageTypeId()):
            # do we have permission ?
            if not self.checkPermission(Permissions.ChangeType,self):
                raise 'Unauthorized', (
                    _("You are not authorized to change this ZWiki Page's type."))
            # is it one of the allowed types for this wiki ?
            #if not type in self.allowedPageTypes():
            #    raise 'Unauthorized', (
            #        _("Sorry, that's not one of the allowed page types in this wiki."))
            # change it
            self.setPageType(type)
            self.preRender(clear_cache=1)
            self.setLastEditor(REQUEST)
            self.setLastLog(log)

        """
        Note log message, if provided.
        """
    def setLastLog(self,log):
        if log and string.strip(log):
            log = string.strip(log)
            get_transaction().note('"%s"' % log)
            self.last_log = log
        else:
            self.last_log = ''


    def handleEditText(self,text,REQUEST=None, subjectSuffix='', log=''):
        # is the new text valid and different ?
        if (text is not None and
            self._cleanupText(text) != self.read()):
            # do we have permission ?
            if (not
                (self.checkPermission(Permissions.Edit, self) or
                 (self.checkPermission(Permissions.Append, self)
                  and find(self._cleanupText(text),self.read()) == 0))):
                raise 'Unauthorized', (
                    _('You are not authorized to edit this ZWiki Page.'))

            # change it
            oldtext = self.read()
            self.setText(text,REQUEST)
            self.setLastEditor(REQUEST)
            self.setLastLog(log)

            # if mailout policy is all edits, do it here
            if getattr(self.folder(),'mailout_policy','')=='edits':
                self.sendMailToSubscribers(
                    self.textDiff(a=oldtext,b=self.read()),
                    REQUEST=REQUEST,
                    subject=log)

    def handleDeleteMe(self,text,REQUEST=None,log=''):
        if not text or not re.match('(?m)^DeleteMe', text):
            return 0
        if (not
            (self.checkPermission(Permissions.Edit, self) or
             (self.checkPermission(Permissions.Append, self)
              and find(self._cleanupText(text),self.read()) == 0))):
            raise 'Unauthorized', (
                _('You are not authorized to edit this ZWiki Page.'))
        if not self.checkPermission(Permissions.Delete, self):
            raise 'Unauthorized', (
                _('You are not authorized to delete this ZWiki Page.'))
        self.setLastLog(log)
        self.recycle(REQUEST)

        if REQUEST:
            # redirect to first existing parent, or front page
            destpage = ''
            for p in self.parents:
                if hasattr(self.folder(),p):
                    destpage = p
                    break
            REQUEST.RESPONSE.redirect(self.wiki_url()+'/'+quote(destpage))
            # I used to think redirect did not return, guess I was wrong

        # return true to terminate edit processing
        return 1

    def handleRename(self,newname,leaveplaceholder,updatebacklinks,
                      REQUEST=None,log=''):
        # rename does everything we need
        return self.rename(newname,
                           leaveplaceholder=leaveplaceholder,
                           updatebacklinks=updatebacklinks,
                           REQUEST=REQUEST)

    security.declareProtected(Permissions.Delete, 'delete')
    def delete(self,REQUEST=None, updatebacklinks=1, pagename=None):
        """
        Delete (move to recycle_bin) this page, if permissions allow.

        If the pagename argument is provided (so named due to the page
        management form), we will try to redirect all links which point to
        this page, to that one. This is like doing a rename except this
        page vanishes in a puff of smoke. See also rename. As with that
        method, an updatebacklinks=0 argument will disable this.

        XXX no it won't ? also, need a flag to disable reparenting
        """
        if not (self.checkPermission(Permissions.Delete, self) and
                self.requestHasSomeId(REQUEST)):
            raise 'Unauthorized', (
                _('You are not authorized to delete this ZWiki Page.'))
        oldname, oldid = self.pageName(), self.getId()
        # update parents attributes to avoid orphans
        self.moveMyChildrenTo(self.primaryParentName())
        # if a replacement page is specified, redirect all our backlinks there
        if pagename and string.strip(pagename):
            self.replaceLinksThroughoutWiki(oldname,pagename,REQUEST)
        # get parent url while we still can
        parenturl = self.primaryParentUrl()
        # unindex (and remove from outline) and move to the recycle bin folder
        self.recycle(REQUEST)
        # notify subscribers if appropriate
        if getattr(self.folder(),'mailout_policy','') == 'edits':
            self.sendMailToSubscribers(
                'This page was deleted.\n',
                REQUEST=REQUEST,
                subjectSuffix='',
                subject='(deleted)')
        if REQUEST: REQUEST.RESPONSE.redirect(parenturl)

    def ensureRecycleBin(self):
        if not hasattr(self.folder(),'recycle_bin'):
            self.folder().manage_addFolder('recycle_bin', 'deleted wiki pages')

    def recycle(self, REQUEST=None):
        """
        Move this page to the recycle_bin subfolder, creating it if necessary.
        """
        self.ensureRecycleBin()
        f = self.folder()
        # cut or paste also unindexes, I believe
        cb = f.manage_cutObjects(self.getId())
        # kludge! don't let manage_pasteObjects catalog the new location
        # (or add it to wiki outline)
        save = self.__class__.manage_afterAdd
        self.__class__.manage_afterAdd = lambda self,item,container: None
        f.recycle_bin.manage_pasteObjects(cb)
        self.__class__.manage_afterAdd = save

    security.declareProtected(Permissions.Rename, 'rename')
    def rename(self,pagename,
               leaveplaceholder=LEAVE_PLACEHOLDER,
               updatebacklinks=0,sendmail=1,REQUEST=None):
        """
        Rename this page, if permissions allow.

        We do various optional extras:
        - preserve parentage of our children
        - update links throughout the wiki. Warning, this may not be 100%
        reliable. It replaces all occurrences of the old page name
        beginning and ending with a word boundary. When changing between a
        wikiname and freeform name, it should do the right thing with
        brackets. It won't change a fuzzy freeform name though.
        - leave a placeholder page
        - notify subscribers
        - if called with the existing name, ensures that id conforms to
        canonicalId(title).
        """
        # anything to do ?
        oldname, oldid = self.pageName(), self.getId()
        newname, newid = pagename, self.canonicalIdFrom(pagename)
        if not newname or (newname == oldname and newid == oldid): return 

        # require a username as well as rename permission for renaming
        if not self.requestHasSomeId(REQUEST):
            raise 'Unauthorized', (
                _('You are not authorized to rename this ZWiki Page.'))

        BLATHER('renaming %s (%s) to %s (%s)...'%(oldname,oldid,newname,newid))

        # an old page just might have an empty title attribute - set it to
        # avoid problems
        if not self.title: self.title = self.getId()

        # has the page name changed ?
        if newname != oldname:
            # update parents attributes (before our name changes)
            self.moveMyChildrenTo(newname)
            # update all links to oldname
            # any later problems will undo all this (yay transactions!)
            if updatebacklinks:
                self.replaceLinksThroughoutWiki(oldname,newname,REQUEST)

        # update wiki outline
        # changeIdPreservingCreator->manage_renameObject->_delObject/_setObject
        # has the effect of losing our place in the hierarchy, take a snapshot
        # so we can fix it up later
        savedparentmap = self.wikiOutline().parentmap().copy()

        # has the page id changed ?
        if newid != oldid:
            # NB manage_renameObject probably does an index_object() too
            self.changeIdPreservingCreator(newid)
            # update wikilinks to our old id, too, if not already done
            # XXX optimisation: this is expensive so do it in one pass
            if updatebacklinks and oldid != oldname:
                self.replaceLinksThroughoutWiki(oldid,newid,REQUEST)

        # change our name
        self.title = newname
        # update catalog
        self.index_object() # XXX creator info may need reindexing too
        # update wiki outline
        self.wikiOutline().setParentmap(savedparentmap)
        self.wikiOutline().replace(oldname,newname)

        # do this after the above so it will have correct parent
        if newid != oldid and leaveplaceholder:
            # the url has changed, leave a placeholder
            try: self.create(oldid,
                             # XXX puts unicode in the page which causes
                             # problems for UnixMailbox later
                             _("This page was renamed to %s. You can delete this one if no longer needed.\n") % (newname),
                             sendmail=0)
            # special case: we'll end up here when first saving a
            # page that was created via the CMF/Plone content
            # management interface - we can't save a placeholder
            # page since the canonical ID hasn't really changed
            except BadRequestException: pass

        # notify subscribers if appropriate
        if (getattr(self.folder(),'mailout_policy','') == 'edits' and
            sendmail and newname != oldname):
            self.sendMailToSubscribers(
                'This page was renamed from %s to %s.\n'%(oldname,newname),
                REQUEST=REQUEST,
                subjectSuffix='',
                subject='(renamed)')

        BLATHER('rename complete')
        if REQUEST: REQUEST.RESPONSE.redirect(self.page_url())

    def changeIdPreservingCreator(self,newid):
        creation_time, creator, creator_ip = \
          self.creation_time, self.creator, self.creator_ip
        self.folder().manage_renameObject(self.getId(),newid)
        self.creation_time, self.creator, self.creator_ip = \
          creation_time, creator, creator_ip

    def moveMyChildrenTo(self,newparent):
        children = self.childrenIdsAsList()
        if children:
            BLATHER('reparenting children of',self.getId())
            for id in children:
                child = getattr(self.folder(),id) # XXX poor caching
                child.removeParent(self.pageName())
                child.addParent(newparent)
                child.index_object() # XXX need only reindex parents
                
        """
        Replace one link with another throughout the wiki.

        Freeform links should not be enclosed in brackets.
        Comes with an appropriately big scary-sounding name. See
        replaceLinks for more.
        """
    def replaceLinksThroughoutWiki(self,oldlink,newlink,REQUEST=None):
        BLATHER('replacing all %s links with %s' % (oldlink,newlink))
        for p in self.backlinksFor(oldlink):
            # regexps may fail on large pages (IssueNo0395), carry on
            # poor caching
            try: p.getObject().replaceLinks(oldlink,newlink,REQUEST)
            except (RuntimeError, AttributeError):
                BLATHER('replaceLinks failed to update %s links in %s' \
                     % (oldlink,p.id))

        """
        Replace occurrences of oldlink with newlink in my text.

        Freeform links should not be enclosed in brackets.
        We'll also replace bare wiki links to a freeform page's id,
        but not fuzzy links.
        This tries not to do too much damage, but is pretty dumb.
        Maybe it should use the pre-linking information.
        It's slow, since it re-renders every page it changes.
        """
    def replaceLinks(self,oldlink,newlink,REQUEST=None):
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
                  REQUEST=REQUEST,
                  log='links updated after rename')

    def handleFileUpload(self,REQUEST,log=''):
        # is there a file upload ?
        if (REQUEST and
            hasattr(REQUEST,'file') and
            hasattr(REQUEST.file,'filename') and
            REQUEST.file.filename):     # XXX do something

            # figure out the upload destination
            if hasattr(self,'uploads'):
                uploaddir = self.uploads
            else:
                uploaddir = self.folder()

            # do we have permission ?
            if not (self.checkPermission(Permissions.Upload,uploaddir)):# or
                    #self.checkPermission(Permissions.UploadSmallFiles,
                    #                self.folder())):
                raise 'Unauthorized', (
                    _('You are not authorized to upload files here.'))
            if not (self.checkPermission(Permissions.Edit, self) or
                    self.checkPermission(Permissions.Append, self)):
                raise 'Unauthorized', (
                    _('You are not authorized to add a link on this ZWiki Page.'))
            # can we check file's size ?
            # yes! len(REQUEST.file.read()), apparently
            #if (len(REQUEST.file.read()) > LARGE_FILE_SIZE and
            #    not self.checkPermission(Permissions.Upload,
            #                        uploaddir)):
            #    raise 'Unauthorized', (
            #        _("""You are not authorized to add files larger than
            #        %s here.""" % (LARGE_FILE_SIZE)))

            # create the File or Image object
            file_id, content_type, size = \
                    self._createFileOrImage(REQUEST.file,
                                            title=REQUEST.get('title', ''),
                                            REQUEST=REQUEST)
            if file_id:
                # link it on the page and finish up
                self._addFileLink(file_id, content_type, size, REQUEST)
                self.setLastLog(log)
                self.index_object()
            else:
                # failed to create - give up (what about an error)
                pass

    def _createFileOrImage(self,file,title='',REQUEST=None,parent=None):
        # based on WikiForNow which was based on
        # OFS/Image.py:File:manage_addFile
        """
        Add a new File or Image object, depending on file's filename
        suffix. Returns a tuple containing the new id, content type &
        size, or (None,None,None).
        """
        # set id & title from filename
        title=str(title)
        id, title = OFS.Image.cookId('', title, file)
        if not id:
            return None, None, None

        # find out where to store files - in an 'uploads'
        # subfolder if defined, otherwise in the wiki folder
        if (hasattr(self.folder().aq_base,'uploads') and
            self.folder().uploads.isPrincipiaFolderish):
            folder = self.folder().uploads
        else:
            folder = parent or self.folder() # see create()

        if hasattr(folder,id) and folder[id].meta_type in ('File','Image'):
            pass
        else:
            # First, we create the file or image object without data
            if guess_content_type(file.filename)[0][0:5] == 'image':
                folder._setObject(id, OFS.Image.Image(id,title,''))
            else:
                folder._setObject(id, OFS.Image.File(id,title,''))

        # Now we "upload" the data.  By doing this in two steps, we
        # can use a database trick to make the upload more efficient.
        folder._getOb(id).manage_upload(file)

        return id, folder._getOb(id).content_type, folder._getOb(id).getSize()

    def _addFileLink(self, file_id, content_type, size, REQUEST):
        """
        Add a link to the specified file at the end of this page,
        unless a link already exists.
        If the file is an image and not too big, inline it instead.
        """
        if re.search(r'(src|href)="%s"' % file_id,self.text()): return

        if hasattr(self,'uploads'):
            filepath = 'uploads/'
        else:
            filepath = ''
        if content_type[0:5] == 'image' and \
           not (hasattr(REQUEST,'dontinline') and REQUEST.dontinline) and \
           size <= LARGE_FILE_SIZE :
            linktxt = '\n\n<img src="%s%s" />\n' % (filepath,file_id)
        else:
            linktxt = '\n\n<a href="%s%s">%s</a>\n' % (filepath,file_id,file_id)
        self.setText(self.read()+linktxt,REQUEST)
        self.setLastEditor(REQUEST)

        """
        Set up the zope ownership of a new page appropriately.
        """
    def _setOwnership(self, REQUEST=None):
        # To help control executable content, make sure the new page
        # acquires it's owner from the parent folder.
        self._deleteOwnershipAfterAdd()
        #if not self.usingRegulations():
        #    # To help control executable content, make sure the new page
        #    # acquires it's owner from the parent folder.
        #    self._deleteOwnershipAfterAdd()
        #else:
        #    self._setOwnerRole(REQUEST)
            
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
            RESPONSE.setHeader('Content-Type', 'text/plain')
            #RESPONSE.setHeader('Last-Modified', rfc1123_date(self._p_mtime))
        return self.read()

    def setText(self, text='', REQUEST=None):
        """
        Change this page's text.

        Does cleanups and triggers pre-rendering and DTML re-parsing.
        Also inserts purple number NIDs if appropriate.
        """
        self.raw = self._cleanupText(text)
        if self.usingPurpleNumbers(): 
            self.raw = self.addPurpleNumbersTo(self.raw,self)
        self.preRender(clear_cache=1)
        # re-cook DTML's cached parse data if necessary
        # will prevent edit if DTML can't parse.. hopefully no auth trouble
        self.cookDtmlIfNeeded()
        # try running the DTML, to prevent edits if DTML can't execute
        # got authorization problems, commit didn't help..
        #if self.supportsDtml() and self.dtmlAllowed():
        #    #get_transaction().commit()
        #    DTMLDocument.__call__(self,self,REQUEST,REQUEST.RESPONSE)

    def _cleanupText(self, t):
        """do some cleanup of a page's new text
        """
        # strip any browser-appended ^M's
        t = re.sub('\r\n', '\n', t)

        # convert international characters to HTML entities for safekeeping
        #for c,e in intl_char_entities:
        #    t = re.sub(c, e, t)
        # assume today's browsers will not harm these.. if this turns out
        # to be false, do some smarter checking here

        # here's the place to strip out any disallowed html/scripting elements
        # XXX there are updates for this somewhere on zwiki.org
        if DISABLE_JAVASCRIPT:
            t = re.sub(javascriptexpr,r'&lt;disabled \1&gt;',t)

        # strip out HTML document header/footer if added
        # XXX these can be expensive, for now just skip if there's a problem
        try:
            t = re.sub(htmlheaderexpr,'',t)
            t = re.sub(htmlfooterexpr,'',t)
        except RuntimeError:
            pass

        return t

    def setLastEditor(self, REQUEST=None):
        """
        record my last_editor & last_editor_ip
        """
        if REQUEST:
            self.last_editor_ip = REQUEST.REMOTE_ADDR
            self.last_editor = self.usernameFrom(REQUEST)
        else:
            # this has been fiddled with before
            # if we have no REQUEST, at least update last editor
            self.last_editor_ip = ''
            self.last_editor = ''
        self.last_edit_time = DateTime(time.time()).ISO()

    def setCreator(self, REQUEST=None):
        """
        record my creator, creator_ip & creation_time
        """
        self.creation_time = DateTime(time.time()).ISO()
        if REQUEST:
            self.creator_ip = REQUEST.REMOTE_ADDR
            self.creator = self.usernameFrom(REQUEST)
        else:
            self.creator_ip = ''
            self.creator = ''

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
            (not hasattr(self,'last_editor') or
             not hasattr(self,'last_editor_ip') or
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

    security.declareProtected(Permissions.Edit, 'PUT')
    def PUT(self, REQUEST, RESPONSE):
        """
        Handle HTTP/FTP/WebDav PUT requests.
        """
        self.dav__init(REQUEST, RESPONSE)
        self.dav__simpleifhandler(REQUEST, RESPONSE, refresh=1)
        body=REQUEST.get('BODY', '')
        self._validateProxy(REQUEST)

        headers, body = parseHeadersBody(body)
        log = string.strip(headers.get('Log', headers.get('log', ''))) or None
        type = (string.strip(headers.get('Type', headers.get('type', '')))
                or None)
        if type is not None:
            type = string.split(type)[0]
            #if type not in self.allowedPageTypes():
            #    # Silently ignore it.
            #    type = None
        timestamp = string.strip(headers.get('Wiki-Safetybelt', '')) or None
        if timestamp and self.checkEditConflict(timestamp, REQUEST):
            RESPONSE.setStatus(423) # Resource Locked
            return RESPONSE

        #self.setText(body)
        #self.setLastEditor(REQUEST)
        #self.index_object()
        #RESPONSE.setStatus(204)
        #return RESPONSE
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
        This wiki's "allowed" page types, ie those offered in the edit form.
        """
        if self.inCMF(): default = ALLOWED_PAGE_TYPES_IN_PLONE
        else: default = ALLOWED_PAGE_TYPES
        allowed = getattr(self,'allowed_page_types',default)
        return filter(lambda x:strip(x),allowed)

    def defaultPageType(self):
        """This wiki's default page type."""
        return self.allowedPageTypes()[0]
    
Globals.InitializeClass(EditingSupport)

