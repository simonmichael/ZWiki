"""
Editing methods.
"""

from __future__ import nested_scopes
import re, string, time
from string import split,join,find,lower,rfind,atoi,strip
from urllib import quote, unquote
from types import *
from email.Message import Message
from copy import deepcopy

import ZODB # need this for pychecker
from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import rfc1123_date
from DateTime import DateTime
from Globals import InitializeClass
try:
    from zope.app.content_types import guess_content_type
except ImportError:
    from OFS.content_types import guess_content_type
from OFS.DTMLDocument import DTMLDocument
from OFS.ObjectManager import BadRequestException
import OFS.Image

from pagetypes import PAGETYPES
from Defaults import DISABLE_JAVASCRIPT, LARGE_FILE_SIZE, LEAVE_PLACEHOLDER
import Permissions
from Regexps import javascriptexpr, htmlheaderexpr, htmlfooterexpr
from Utils import get_transaction, BLATHER, parseHeadersBody
from I18n import _


class PageEditingSupport:
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
    def checkPermission(self, permission, object):
        return getSecurityManager().checkPermission(permission,object)

    security.declareProtected(Permissions.Add, 'create') 
    def create(self,page=None,text='',type=None,title='',REQUEST=None,log='',
               sendmail=1, parents=None, subtopics=None, pagename=None):
        """
        Create a new wiki page, with optional extras.

        Normally edit() will call this for you. 

        We assume the page name comes url-quoted. If it's not a url-safe
        name, we will create the page with a similar url-safe id, which we
        assume won't match any existing page (or zwiki would have linked
        instead of offering to create). Also it allows the alternate pagename
        argument, to support the page management form (XXX temporary).
        Other features:

        - can upload a file at the same time.  

        - can set the subtopics display property

        - can handle a rename during page creation. This helps CMF/Plone
        and is occasionally useful.
        
        - checks the edit_needs_username property as well as permissions.

        - redirects to the new page or to the denied view if appropriate

        - returns the new page's name or None

        """
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
        # newid should be the same as id, but don't assume
        newid = self.folder()._setObject(id,p)
        p = getattr(self.folder(),newid)

        p.checkForSpam(text)
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
        #if p.usingRegulations(): p.setRegulations(REQUEST,new=1)
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
        (move it to the /recycle_bin)

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
        p.handleEditPageType(type,REQUEST,log)
        if text != None: p.handleEditText(text,REQUEST,subjectSuffix,log)
        p.handleSubtopicsProperty(subtopics,REQUEST)
        p.handleFileUpload(REQUEST,log)
        p.handleRename(title,leaveplaceholder,updatebacklinks,REQUEST,log)
        #if self.usingRegulations(): p.handleSetRegulations(REQUEST)

        p.index_object()

        # tell browser to reload the page (or redirect elsewhere)
        if REQUEST:
            try:
                REQUEST.RESPONSE.redirect(
                    (REQUEST.get('redirectURL',None) or
                     REQUEST['URL2']+'/'+ quote(p.id())))
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
        old = self.read()
        new = self.cleanupText(text)
        # is the new text different ?
        if new != old:
            # do we have permission ?
            if (not
                (self.checkPermission(Permissions.Edit, self) or
                 (self.checkPermission(Permissions.Comment, self)
                  and find(new,old) == 0))):
                raise 'Unauthorized', (
                    _('You are not authorized to edit this ZWiki Page.'))

            # does this edit look like spam ?
            # Tries to count the links added by this edit. Not perfect -
            # existing links on a line that you tweak will be counted.
            # Not sure what happens if you replace existing links.
            self.checkForSpam(self.addedText(old, new))
                
            # change it
            self.setText(text,REQUEST)
            self.setLastEditor(REQUEST)
            self.setLastLog(log)

            # send mail if appropriate
            self.sendMailToEditSubscribers(
                self.textDiff(a=old,b=self.read()),
                REQUEST=REQUEST,
                subject='(edit) %s' % log)

    def handleDeleteMe(self,text,REQUEST=None,log=''):
        if not text or not re.match('(?m)^DeleteMe', text):
            return 0
        if (not
            (self.checkPermission(Permissions.Edit, self) or
             (self.checkPermission(Permissions.Comment, self)
              and find(self.cleanupText(text),self.read()) == 0))):
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
        oldname, oldid = self.pageName(), self.getId()
        # update parents attributes to avoid orphans
        self.moveMyChildrenTo(self.primaryParentName())
        # if a replacement page is specified, redirect all our backlinks there
        if pagename and string.strip(pagename):
            self.replaceLinksThroughoutWiki(oldname,pagename,REQUEST)
        # get parent url while we still can
        redirecturl = self.upUrl()
        # unindex (and remove from outline) and move to the recycle bin folder
        self.recycle(REQUEST)
        # notify subscribers if appropriate
        self.sendMailToEditSubscribers(
            'This page was deleted.\n',
            REQUEST=REQUEST,
            subjectSuffix='',
            subject='(deleted)')
        if REQUEST: REQUEST.RESPONSE.redirect(redirecturl)

    def ensureRecycleBin(self):
        if not hasattr(self.folder().aq_base,'recycle_bin'):
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
               updatebacklinks=1,
               sendmail=1,
               REQUEST=None):
        """
        Rename this page, if permissions allow.

        Another method that does quite a lot. Extras:
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

        XXX the sendmail argument doesn't stop mailouts from updating backlinks
        """
        # anything to do ?
        oldname, oldid = self.pageName(), self.getId()
        # newlines would cause glitches later..
        pagename = re.sub(r'[\r\n]','',pagename)
        newname, newid = pagename, self.canonicalIdFrom(pagename)
        if not newname or (newname == oldname and newid == oldid): return 

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
        # -> manage_after* has the effect of losing our place in the
        # hierarchy, take a snapshot so we can fix it up later
        savedparentmap = deepcopy(self.wikiOutline().parentmap())
        savedchildmap = deepcopy(self.wikiOutline().childmap())

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
        # update wiki outline, using the copy we saved earlier
        # nb that outline may not have been up to date, but replace will forgive
        self.wikiOutline().setParentmap(savedparentmap)
        self.wikiOutline().setChildmap(savedchildmap)
        self.wikiOutline().replace(oldname,newname)

        # do this after the above so it will have correct parent
        if (newid != oldid) and leaveplaceholder:
            # the url has changed, leave a placeholder
            try: self.create(oldid,
                             _("This page was renamed to %s. You can delete this one if no longer needed.\n") % (newname),
                             sendmail=0)
            # special case: we'll end up here when first saving a
            # page that was created via the CMF/Plone content
            # management interface - we can't save a placeholder
            # page since the canonical ID hasn't really changed
            except BadRequestException: pass

        # notify subscribers if appropriate
        if sendmail and newname != oldname:
            self.sendMailToEditSubscribers(
                'This page was renamed from %s to %s.\n'%(oldname,newname),
                REQUEST=REQUEST,
                subjectSuffix='',
                subject='(renamed)')

        BLATHER('rename complete')
        if REQUEST: REQUEST.RESPONSE.redirect(self.pageUrl())

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
            # this is an extensive, risky operation which can fail for
            # a number of reasons - carry on regardless so we don't
            # block renames
            # poor caching
            try: p.getObject().replaceLinks(oldlink,newlink,REQUEST)
            except:
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
                  REQUEST=REQUEST)

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
                    self.checkPermission(Permissions.Comment, self)):
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

    def _createFileOrImage(self,file,title='',REQUEST=None):
        # based on WikiForNow which was based on
        # OFS/Image.py:File:manage_addFile
        """
        Add a new File or Image object, depending on file's filename
        suffix. Returns a tuple containing the new id, content type &
        size, or (None,None,None).
        """
        # macro to check folder contents without acquiring
        folderHas = lambda folder,id: hasattr(folder.aq_base,id)

        # set id & title from filename
        title=str(title)
        id, title = OFS.Image.cookId('', title, file)
        if not id:
            return None, None, None

        # find out where to store files - in an 'uploads' subfolder if
        # present, otherwise the wiki folder
        folder = self.folder()
        if (folderHas(folder,'uploads') and
            folder.uploads.isPrincipiaFolderish):
            folder = folder.uploads

        # unless it already exists, create the file or image object
        # use the CMF/Plone types if appropriate
        # it will be renamed if there is an id collision with some other
        # kind of object
        if not (folderHas(folder,id) and
                folder[id].meta_type in ('File','Image')):#,
                                         #'Portal File','Portal Image')):
            if guess_content_type(file.filename)[0][0:5] == 'image':
                if self.inCMF():
                    #XXX how ?
                    id = folder._setObject(id, OFS.Image.Image(id,title,'')) 
                else:
                    id = folder._setObject(id, OFS.Image.Image(id,title,''))
            else:
                if self.inCMF():
                    #XXX how ?
                    id = folder._setObject(id, OFS.Image.File(id,title,''))
                else:
                    id = folder._setObject(id, OFS.Image.File(id,title,''))

        # Now we "upload" the data.  By doing this in two steps, we
        # can use a database trick to make the upload more efficient. (?)
        ob = folder._getOb(id)
        ob.manage_upload(file)

        return (id, ob.content_type, ob.getSize())

    def _addFileLink(self, file_id, content_type, size, REQUEST):
        """
        Link a file or image at the end of this page, if not already linked.
        
        If it's an image and not too big, display it inline.
        """
        if re.search(r'(src|href)="%s"' % file_id,self.text()): return

        if hasattr(self,'uploads'): folder = 'uploads/'
        else: folder = ''

        if content_type[0:5] == 'image' and \
           not (hasattr(REQUEST,'dontinline') and REQUEST.dontinline) and \
           size <= LARGE_FILE_SIZE :
            linktxt = self.pageType().inlineImage(self, file_id, folder+file_id)
        else:
            linktxt = self.pageType().linkFile(self, file_id, folder+file_id)
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

        # anonymous edit with too many urls ?
        prop = 'max_anonymous_links'
        # we'll handle either an int or string property
        if (not self.requestHasUsername(REQUEST) and
            hasattr(self.folder(), prop)):
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
        if (hasattr(self.folder(), prop)):
            try: max = int(getattr(self.folder(), prop))
            except ValueError: max = None
            if max is not None:
                if len(re.findall(r'https?://',t)) > max:
                    raiseSpamError(_("exceeded max_identified_links"),
                                   _("adding of external links is restricted, even for identified users. Please back up and remove some of the http urls you added, or contact the site administrator for help."))

    def cleanupText(self, t):
        """
        Do some cleanup of incoming text, also block spam links.
        """
        # strip any browser-appended ^M's
        t = re.sub('\r\n', '\n', t)

        # XXX epoz & dtml compatibility
        # editing a page with Epoz changes
        # <dtml-var "TestPage(bare=1,REQUEST=REQUEST)"> to
        # <dtml-var ="" testpage(bare="1,REQUEST=REQUEST)&quot;"></dtml-var>
        #
        # <dtml-var expr="TestPage(bare=1,REQUEST=REQUEST)"> does better
        # but still gets a </dtml-var> added.. we can strip this.  At
        # least now a dtml page or method can be included safely in an
        # epoz page.
        #BLATHER('text from epoz:',t[:100])
        #t = re.sub(r'</dtml-var>','',t)
        #BLATHER('saving text:',t[:100])

        # convert international characters to HTML entities for safekeeping
        #for c,e in intl_char_entities:
        #    t = re.sub(c, e, t)
        # assume today's browsers will not harm these.. if this turns out
        # to be false, do some smarter checking here

        # here's the place to strip out any disallowed html/scripting elements
        # XXX there are updates for this somewhere on zwiki.org
        if DISABLE_JAVASCRIPT:
            t = re.sub(javascriptexpr,r'&lt;disabled \1&gt;',t)

        # strip out HTML header tags if present
        def onlyBodyFrom(t):
            # XXX these can be expensive, for now just skip if there's a problem
            try:
                t = re.sub(htmlheaderexpr,'',t)
                t = re.sub(htmlfooterexpr,'',t)
            except RuntimeError: pass
            return t
            # maybe better, but more inclined to mess with valid text ?
            #return re.sub(htmlbodyexpr, r'\1', t)
        t = onlyBodyFrom(t)

        return t

    def setLastEditor(self, REQUEST=None):
        """
        Record last editor info based on the current REQUEST and time.
        """
        if REQUEST:
            self.last_editor_ip = REQUEST.REMOTE_ADDR
            self.last_editor = self.usernameFrom(REQUEST)
        else:
            # this has been fiddled with before
            # if we have no REQUEST, at least update last editor
            self.last_editor_ip = ''
            self.last_editor = ''
        self.last_edit_time = DateTime(time.time()).toZone('UTC').ISO()

    def hasCreatorInfo(self):
        """
        True if this page already has creator attributes.
        """
        return (hasattr(self,'creator') and
                hasattr(self,'creation_time') and
                hasattr(self,'creator_ip'))
                

    def setCreator(self, REQUEST=None):
        """
        record my creator, creator_ip & creation_time
        """
        self.creation_time = DateTime(time.time()).toZone('UTC').ISO()
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
        log = string.strip(headers.get('Log', headers.get('log', ''))) or ''
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

