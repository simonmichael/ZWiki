# Admin.py - methods supporting wiki administration

from types import *
import os, re, os.path
from string import join, split, strip

from AccessControl import getSecurityManager, ClassSecurityInfo
import Permissions
from Globals import package_home
from OFS.CopySupport import CopyError
from OFS.DTMLMethod import DTMLMethod
from LocalizerSupport import LocalDTMLFile, _, N_
from App.Common import absattr
from DateTime import DateTime

from Utils import BLATHER,formattedTraceback, DateTimeSyntaxError
from Defaults import ISSUE_CATEGORIES, ISSUE_SEVERITIES, ISSUE_STATUSES, \
     ISSUE_COLOURS

# if page types are states, here is the table of transitions for upgrading
PAGE_TYPE_UPGRADES = {
    # early zwiki
    'Structured Text'           :'msgstxprelinkdtmlfitissuehtml',
    'structuredtext_dtml'       :'msgstxprelinkdtmlfitissuehtml',
    'HTML'                      :'dtmlhtml',
    'html_dtml'                 :'dtmlhtml',
    'Classic Wiki'              :'msgwwmlprelinkfitissue',
    'Plain Text'                :'plaintext',
    # pre-0.9.10
    'stxprelinkdtml'            :'msgstxprelinkdtmlfitissuehtml',
    'structuredtextdtml'        :'msgstxprelinkdtmlfitissuehtml',
    'dtmlstructuredtext'        :'msgstxprelinkdtmlfitissuehtml',
    'structuredtext'            :'msgstxprelinkdtmlfitissuehtml',
    'structuredtextonly'        :'msgstxprelinkdtmlfitissuehtml',
    'classicwiki'               :'msgwwmlprelinkfitissue',
    'htmldtml'                  :'dtmlhtml',
    'plainhtmldtml'             :'dtmlhtml',
    'plainhtml'                 :'dtmlhtml',
    # pre-0.17
    'stxprelinkdtmlhtml'        :'msgstxprelinkdtmlfitissuehtml',
    'issuedtml'                 :'msgstxprelinkdtmlfitissuehtml',
    # pre-0.19
    'stxdtmllinkhtml'           :'msgstxprelinkdtmlfitissuehtml',
    'dtmlstxlinkhtml'           :'msgstxprelinkdtmlfitissuehtml',
    'stxprelinkhtml'            :'msgstxprelinkdtmlfitissuehtml',
    'stxlinkhtml'               :'msgstxprelinkdtmlfitissuehtml',
    'stxlink'                   :'msgstxprelinkdtmlfitissuehtml',
    'wwmllink'                  :'msgwwmlprelinkfitissue',
    'wwmlprelink'               :'msgwwmlprelinkfitissue',
    'prelinkdtmlhtml'           :'dtmlhtml',
    'dtmllinkhtml'              :'dtmlhtml',
    'prelinkhtml'               :'dtmlhtml',
    'linkhtml'                  :'dtmlhtml',
    'textlink'                  :'plaintext',
    # pre-0.20
    'stxprelinkfitissue'        :'msgstxprelinkdtmlfitissuehtml',
    'stxprelinkfitissuehtml'    :'msgstxprelinkdtmlfitissuehtml',
    'stxprelinkdtmlfitissuehtml':'msgstxprelinkdtmlfitissuehtml',
    'rstprelinkfitissue'        :'msgrstprelinkfitissue',
    'wwmlprelinkfitissue'       :'msgwwmlprelinkfitissue',
    # pre-0.22
    'msgstxprelinkfitissuehtml' :'msgstxprelinkdtmlfitissuehtml',
    'html'                      :'dtmlhtml',
    }

# copied from ZWikiWeb.py
def _addDTMLMethod(self, id, title='', file=''):
    id=str(id)
    title=str(title)
    ob = DTMLMethod(source_string=file, __name__=id)
    ob.title = title
    username = getSecurityManager().getUser().getUserName()
    ob.manage_addLocalRoles(username, ['Owner'])
    #ob.setSubOwner('both') #?
    self._setObject(id, ob)

class AdminSupport:
    """
    This mix-in class provides some utilities to ease wiki administration.
    """
    security = ClassSecurityInfo()

    security.declarePublic('upgradeAll') # check folder permission at runtime
    def upgradeAll(self,pre_render=1,upgrade_messages=0,check_parents=1,
                   REQUEST=None):
        """
        Clear cache, upgrade and pre-render all pages

        Normally pages are upgraded/pre-rendered as needed.  An
        administrator may want to call this, particularly after a zwiki
        upgrade, to minimize later delays and to ensure all pages have
        been rendered by the latest code.

        Requires 'Manage properties' permission on the folder.
        Commit every so often an attempt to avoid memory/conflict errors.
        Has problems doing a complete run in large wikis, or when other
        page accesses are going on ?
        """
        if not self.checkPermission(Permissions.manage_properties,
                                     self.folder()):
            raise 'Unauthorized', (
             _('You are not authorized to upgrade all pages.') + \
             _('(folder -> Manage properties)'))
        try: pre_render = int(pre_render)
        except: pre_render = 0
        if pre_render:
            BLATHER('upgrading and prerendering all pages:')
        else:
            BLATHER('upgrading all pages:')
        n = 0
        # poor caching (ok in this case)
        for p in self.pageObjects():
            n = n + 1
            try:
                p.upgrade(REQUEST)
                p.upgradeId(REQUEST)
                if pre_render: p.preRender(clear_cache=1)
                if upgrade_messages: p.upgradeMessages(REQUEST)
                if check_parents: p.checkParents(update_outline=0)
                BLATHER('upgraded page #%d %s'%(n,p.id()))
            except:
                BLATHER('failed to upgrade page #%d %s: %s' \
                     % (n,p.id(),formattedTraceback()))
            if n % 100 == 0:
                BLATHER('committing')
                # do this at each commit just in case
                if check_parents: self.updateWikiOutline()
                get_transaction().commit()
        # last pages will get committed as this request ends
        # but finish this.. probably good to do in any case
        self.updateWikiOutline()
        BLATHER('upgrade complete, %d pages processed' % n)

    #security.declarePublic('upgradeId')
    security.declareProtected(Permissions.View, 'upgradeId')
    def upgradeId(self,REQUEST=None):
        """
        Make sure a page's id conforms with it's title, renaming as needed.

        Does not leave a placeholder, so may break incoming links.
        Presently too slow for auto-upgrade, so people must call this
        manually or via upgradeAll.

        updatebacklinks=1 is used even though it's slow, because it's less
        work than fixing up links by hand afterward.

        With legacy pages (or manually renamed pages), it may happen that
        there's a clash between two similarly-named pages mapping to the
        same canonical id. In this case we just log the error and move on.
        """
        id, cid = self.getId(), self.canonicalId()
        if id != cid:
            oldtitle = title = self.title_or_id()
            # as a special case, preserve tracker issue numbers in the title
            m = re.match(r'IssueNo[0-9]+$',id)
            if m:
                title = '%s %s' % (m.group(),self.title)
            try:
                self.rename(title,updatebacklinks=1,sendmail=0,REQUEST=REQUEST)
            except CopyError:
                BLATHER('failed to rename "%s" (%s) to "%s" (%s) - id clash ?' \
                     % (oldtitle,id,title,self.canonicalIdFrom(title)))

    # performance-sensitive ?
    security.declareProtected(Permissions.View, 'upgrade')
    def upgrade(self,REQUEST=None):
        """
        Upgrade an old page instance (and possibly the parent folder).

        Called on every page view (set AUTO_UPGRADE=0 in Default.py to
        prevent this).  You could also call this on every page in your
        wiki to do a batch upgrade. Affects bobobase_modification_time. If
        you later downgrade zwiki, the upgraded pages may not work so
        well.
        """
        # Note that the objects don't get very far unpickling, some
        # by-hand adjustment via command-line interaction is necessary
        # to get them over the transition, sigh. --ken
        # not sure what this means --SM

        # What happens in the zodb when class definitions change ? I think
        # all instances in the zodb conform to the new class shape
        # immediately on refresh/restart, but what happens to
        # (a) old _properties lists ? not sure, assume they remain in
        # unaffected and we need to add the new properties
        # and (b) old properties & attributes no longer in the class
        # definition ?  I think these lurk around, and we need to delete
        # them.

        changed = 0

        # As of 0.17, page ids are always canonicalIdFrom(title); we'll
        # rename to conform with this where necessary
        # too slow!
        # changed = self.upgradeId()

        # fix up attributes first, then properties
        # don't acquire while doing this
        realself = self
        self = self.aq_base
        # XXXXXXXXXXXXXXXXX WATCH OUT! XXXXXXXXXXXXXXXXXX
        # use realself below if you want normal behaviour
        # this will bite you and cause you to waste time
        # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

        # migrate a WikiForNow _st_data attribute
        if hasattr(self, '_st_data'):
            self.raw = self._st_data
            del self._st_data
            changed = 1

        # upgrade old page types
        if self.pageTypeId() in PAGE_TYPE_UPGRADES.keys():
            self.setPageType(PAGE_TYPE_UPGRADES[self.pageTypeId()])
            # clear render cache; don't bother prerendering just now
            self.clearCache()
            changed = 1

        # Pre-0.9.10, creation_time has been a string in custom format and
        # last_edit_time has been a DateTime. Now both are kept as
        # ISO-format strings. Might not be strictly necessary to upgrade
        # in all cases.. will cause a lot of bobobase_mod_time
        # updates.. do it anyway.
        if not self.last_edit_time:
            self.last_edit_time = self.bobobase_modification_time().ISO()
            changed = 1
        elif type(self.last_edit_time) is not StringType:
            self.last_edit_time = self.last_edit_time.ISO()
            changed = 1
        elif len(self.last_edit_time) != 19:
            try: 
                self.last_edit_time = DateTime(self.last_edit_time).ISO()
                changed = 1
            except DateTimeSyntaxError:
                # can't convert to ISO, just leave it be
                pass

        # If no creation_time, just leave it blank for now.
        # we shouldn't find DateTimes here, but check anyway
        if not self.creation_time:
            pass
        elif type(self.creation_time) is not StringType:
            self.creation_time = self.creation_time.ISO()
            changed = 1
        elif len(self.creation_time) != 19:
            try: 
                self.creation_time = DateTime(self.creation_time).ISO()
                changed = 1
            except DateTimeSyntaxError:
                # can't convert to ISO, just leave it be
                pass

        # _wikilinks, _links and _prelinked are no longer used
        for a in (
            '_wikilinks',
            '_links',
            '_prelinked',
            ):
            #if hasattr(self.aq_base,a): #XXX why doesn't this work
            if hasattr(self,a):
                delattr(self,a)
                self.clearCache()
                changed = 1 

        # update _properties
        # keep in sync with _properties above. Better if we used that as
        # the template (efficiently)
        oldprops = { # not implemented
            'page_type'     :{'id':'page_type','type':'string'},
            }
        newprops = {
            #'page_type'     :{'id':'page_type','type':'selection','mode': 'w',
            #                  'select_variable': 'ZWIKI_PAGE_TYPES'},
            'creator'       :{'id':'creator','type':'string','mode':'r'},
            'creator_ip'    :{'id':'creator_ip','type':'string','mode':'r'},
            'creation_time' :{'id':'creation_time','type':'string','mode':'r'},
            'last_editor'   :{'id':'last_editor','type':'string','mode':'r'},
            'last_editor_ip':{'id':'last_editor_ip','type':'string','mode':'r'},
            'last_edit_time':{'id':'creation_time','type':'string','mode':'r'},
            'last_log'      :{'id':'last_log', 'type': 'string', 'mode': 'r'},
            'NOT_CATALOGED' :{'id':'NOT_CATALOGED', 'type': 'boolean', 'mode': 'w'},
            }
        props = map(lambda x:x['id'], self._properties)
        for p in oldprops.keys():
            if p in props: # and oldprops[p]['type'] != blah blah blah :
                pass
                #ack!
                #self._properties = filter(lambda x:x['id'] != p,
                #                          self._properties)
                #changed = 1
                # XXX this does work in python 1.5 surely.. what's the
                # problem ?
        for p in newprops.keys():
            if not p in props:
                self._properties = self._properties + (newprops[p],)
                changed = 1

        # install issue properties if needed, ie if this page is being
        # viewed as an issue for the first time
        # could do this in isIssue instead
        if (realself.isIssue() and not 'severity' in props):
            # may need to set these up too
            folder = realself.folder()
            if (not hasattr(folder,'issue_categories') or
                not hasattr(folder,'issue_severities') or
                not hasattr(folder,'issue_statuses')):
                realself.setupIssuePropertyValues()
            realself.manage_addProperty('category','issue_categories','selection')
            realself.manage_addProperty('severity','issue_severities','selection')
            realself.manage_addProperty('status','issue_statuses','selection')
            realself.severity = 'normal'
            changed = 1

        if changed:
            # bobobase_modification_time changed - put in a dummy user so
            # it's clear this was not an edit
            # no - you should be looking at last_edit_times, in which case
            # you don't want to see last_editor change for this.
            #self.last_editor_ip = ''
            #self.last_editor = 'UpGrade'
            # do a commit now so the current render will have the
            # correct bobobase_modification_time for display (many
            # headers/footers still show it)
            get_transaction().commit()
            # and log it
            BLATHER('upgraded '+self.id())

        # finally, MailSupport does a bit more (merge here ?)
        realself._upgradeSubscribers()

    security.declareProtected('Manage properties', 'setupPages')
    def setupPages(self,REQUEST=None):
        """
        Install some default wiki pages to help get a wiki started.
        """
        # copied from ZWikiWeb.py
        dir = package_home(globals()) + os.sep + 'content' + os.sep + 'basic'
        filenames = os.listdir(dir)
        for filename in filenames:
            if filename[-5:] == '.dtml': pass
            else:
                m = re.search(r'(.+)\.(.+)',filename)
                if m:
                    name, type = m.group(1), m.group(2)
                    if not self.pageWithName(name):
                        text=open(dir+os.sep+filename,'r').read()
                        # parse optional parents list
                        m = re.match(r'(?si)(^#parents:(.*?)\n)?(.*)',text)
                        if m.group(2): parents = split(strip(m.group(2)),',')
                        else: parents = []
                        text = m.group(3)
                        self.create(name,text=text)
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.page_url())

    security.declareProtected('Manage properties', 'setupPages')
    def setupDtmlPages(self,REQUEST=None):
        """
        Install the DTML page implementations of some standard views.
        This facilitates easy tweaking and development.
        """
        # copied from ZWikiWeb.py
        # XXX extract
        dir = package_home(globals()) + os.sep + 'content' + os.sep + 'dtml'
        filenames = os.listdir(dir)
        for filename in filenames:
            if filename[-5:] == '.dtml': pass
            else:
                m = re.search(r'(.+)\.(.+)',filename)
                if m:
                    name, type = m.group(1), m.group(2)
                    if not self.pageWithName(name):
                        text=open(dir+os.sep+filename,'r').read()
                        # parse optional parents list
                        m = re.match(r'(?si)(^#parents:(.*?)\n)?(.*)',text)
                        if m.group(2): parents = split(strip(m.group(2)),',')
                        else: parents = []
                        text = m.group(3)
                        self.create(name,text=text)
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.page_url())

    security.declareProtected('Manage properties', 'setupDtmlMethods')
    def setupDtmlMethods(self,REQUEST=None):
        """
        Install some default DTML methods to make (non-CMF) wikis work better.
        """
        # copied from ZWikiWeb.py
        dir = package_home(globals()) + os.sep + 'content' + os.sep + 'basic'
        filenames = os.listdir(dir)
        for filename in filenames:
            name, suffix = filename[:-5], filename[-5:]
            if (suffix == '.dtml' and
                not hasattr(self.folder().aq_base,name)):
                _addDTMLMethod(self.folder(),name,title='',
                               file=open(dir+os.sep+filename,'r').read())
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.page_url())

    security.declareProtected('Manage properties', 'setupProperties')
    def setupProperties(self,REQUEST=None):
        """
        Install some of the optional Zwiki properties on this wiki folder.

        Calling this should not change the wiki's behaviour, but puts
        some of the properties in place so that people don't have to
        look up QuickReference.

        XXX But actually, we may want to avoid pre-installing properties
        before they're needed since they increase complexity for the wiki
        admin. Need this ?
        """
        pass
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.page_url())

    security.declareProtected('Manage properties', 'setupCatalog')
    def setupCatalog(self,REQUEST=None,reindex=1):
        """
        Create and/or configure a catalog for this wiki.

        Safe to call more than once; will ignore any already existing
        items.  Based on the data at http://zwiki.org/ZwikiAndZCatalog ;
        see also PAGE_METADATA.
        """
        TextIndexes = [
            'Title',
            'text',
            ]
        #XXX correct choice of FieldIndexes vs. KeywordIndexes ?
        FieldIndexes = [
            'creation_time',
            'creator',
            'id',
            'last_edit_time',
            'last_editor',
            'meta_type',
            'page_type',
            'rating',
            'voteCount',
            ]
        KeywordIndexes = [
            'canonicalLinks',
            #'links', # XXX problems for epoz/plone, not needed ?
            'parents',
            ]
        DateIndexes = [
            'creationTime',
            'lastEditTime',
            ]
        PathIndexes = [
            'path',
            ]
        metadata = [
            'Title',
            'creation_time',
            'creator',
            'id',
            'lastEditTime',
            'last_edit_time',
            'last_editor',
            'last_log',
            #'links', # XXX problems for epoz/plone, not needed ?
            'page_type',
            'parents',
            'size',
            'subscriber_list',
            'summary',
            'rating',
            'voteCount',
            ]
        #XXX during unit testing, somehow a non-None catalog is false
        #if not self.catalog():
        if self.catalogId() == 'NONE':
            # should we still support SITE_CATALOG ? for now, if it exists
            # give the new catalog that name so we will find it
            folder = self.folder()
            id = getattr(folder,'SITE_CATALOG','Catalog')
            folder.manage_addProduct['ZCatalog'].manage_addZCatalog(id,'')
        catalog = self.catalog()
        catalogindexes, catalogmetadata = catalog.indexes(), catalog.schema()
        PluginIndexes = catalog.manage_addProduct['PluginIndexes']
        for i in TextIndexes:
            # XXX should choose a TING2 or ZCTI here and set up appropriately
            # a TextIndex is case sensitive, exact word matches only
            # a ZCTextIndex can be case insensitive and do right-side wildcards
            # a TextIndexNG2 can be case insensitive and do both wildcards
            if not i in catalogindexes: PluginIndexes.manage_addTextIndex(i)
        for i in FieldIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addFieldIndex(i)
        for i in KeywordIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addKeywordIndex(i)
        for i in DateIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addDateIndex(i)
        for i in PathIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addPathIndex(i)
        for m in metadata:
            if not m in catalogmetadata: catalog.manage_addColumn(m)
        if reindex:
            # now index each page, to make all indexes and metadata current
            n = 0
            cid = self.catalog().getId()
            for p in self.pageObjects():
                n = n + 1
                try:
                    BLATHER('indexing page #%d %s in %s'%(n,p.id(),cid))
                    p.index_object(log=0)
                except:
                    BLATHER('failed to index page #%d %s: %s' \
                            % (n,p.id(),formattedTraceback()))
            BLATHER('indexing complete, %d pages processed' % n)
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.page_url())
            
    security.declareProtected('Manage properties', 'setupTracker')
    def setupTracker(self,REQUEST=None,pages=0):
        """
        Configure this wiki for issue tracking.

        This
        - sets up the necessary extra catalog fields
        - sets up issue_* folder properties, for customizing
        - creates a dummy issue, if needed, to activate the issue links/tabs
        - if pages=1, installs forms as DTML pages, for easy customizing
        
        Safe to call more than once; will ignore any already existing
        items.  Based on the setupIssueTracker.py external method and the
        data at http://zwiki.org/ZwikiAndZCatalog.
        """
        TextIndexes = [
            ]
        FieldIndexes = [
            'category',
            'category_index',
            'isIssue',
            'severity',
            'severity_index',
            'status',
            'status_index',
            ]
        KeywordIndexes = [
            ]
        DateIndexes = [
            ]
        PathIndexes = [
            ]
        metadata = [
            'category',
            'category_index',
            'issueColour',
            'severity',
            'severity_index',
            'status',
            'status_index',
            ]
        # make sure we have a basic zwiki catalog set up
        self.setupCatalog(reindex=0)
        catalog = self.catalog()
        catalogindexes, catalogmetadata = catalog.indexes(), catalog.schema()
        PluginIndexes = catalog.manage_addProduct['PluginIndexes']
        # add indexes,
        for i in TextIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addTextIndex(i)
        for i in FieldIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addFieldIndex(i)
        for i in KeywordIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addKeywordIndex(i)
        for i in DateIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addDateIndex(i)
        for i in PathIndexes:
            if not i in catalogindexes: PluginIndexes.manage_addPathIndex(i)
        # metadata,
        for m in metadata:
            if not m in catalogmetadata: catalog.manage_addColumn(m)
        # properties,
        self.setupIssuePropertyValues()
        # dtml pages,
        if pages:
            dir = package_home(globals())+os.sep+'content'+os.sep+'tracker'+os.sep
            for page in ['IssueTracker','FilterIssues']:
                if not self.pageWithName(page):
                    self.create(page,text=open(dir+page+'.stxdtml','r').read())
        # index each page, to make all indexes and metadata current
        # may duplicate some work in setupCatalog
        n = 0
        cid = self.catalog().getId()
        for p in self.pageObjects():
            n = n + 1
            try:
                BLATHER('indexing page #%d %s in %s'%(n,p.id(),cid))
                p.index_object(log=0)
            except:
                BLATHER('failed to index page #%d %s: %s' \
                        % (n,p.id(),formattedTraceback()))
        BLATHER('indexing complete, %d pages processed' % n)
        # and a dummy issue to enable site navigation links
        if not self.hasIssues():
            self.createNextIssue(
                'first issue',
                'This issue was created to activate the issue tracker links/tabs. You can re-use it.',
                ISSUE_CATEGORIES[-1],
                ISSUE_SEVERITIES[-1],
                ISSUE_STATUSES[-1],
                REQUEST=REQUEST)
        if REQUEST: REQUEST.RESPONSE.redirect(self.trackerUrl())

    def setupIssuePropertyValues(self):
        folder = self.folder()
        existingprops = map(lambda x:x['id'], folder._properties)
        for property, values in [
            ['issue_severities',ISSUE_SEVERITIES],
            ['issue_categories',ISSUE_CATEGORIES],
            ['issue_statuses',ISSUE_STATUSES],
            ['issue_colours',ISSUE_COLOURS],
            ]:
            if not property in existingprops:
                folder.manage_addProperty(property,join(values,'\n'),'lines')
