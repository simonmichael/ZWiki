# Admin.py - methods supporting wiki administration

from types import *
import os, re, os.path
from string import join, split, strip
from time import clock

from AccessControl import getSecurityManager, ClassSecurityInfo, Unauthorized
from AccessControl.class_init import InitializeClass
from App.Common import package_home
from OFS.CopySupport import CopyError
from OFS.DTMLMethod import DTMLMethod
from DateTime import DateTime

from i18n import _
import Permissions
from Utils import get_transaction, BLATHER, formattedTraceback, \
     DateTimeSyntaxError, callHooks, isunicode, safe_hasattr
from plugins.pagetypes import PAGE_TYPE_UPGRADES, PAGE_TYPES, modernPageTypeFor
from Defaults import PAGE_METADATA, \
     TEXTINDEXES, FIELDINDEXES, KEYWORDINDEXES, DATEINDEXES, PATHINDEXES


class PageAdminSupport:
    """
    This mix-in class provides some utilities to ease wiki administration.
    """
    security = ClassSecurityInfo()

    security.declarePublic('upgradeAll') # we check folder permission at runtime
    def upgradeAll(self,render=1,batch=0,REQUEST=None): # -> none
        # depends on: wiki
        # modifies: wiki (folder, pages, dtml methods, catalog, outline, revisions..)
        """
        Update, upgrade, pre-render and re-index all pages and data structures.

        Normally individual pages are upgraded and pre-rendered on
        demand, when viewed. An administrator may want to do this for
        all pages ahead of time, particularly after a zwiki upgrade,
        to ensure all pages have the latest properties and have been
        rendered by the latest code, minimizing delay and possible
        problems later on.

        Also installs a wiki catalog if not present, re-indexes each
        page, validates page parents, and rebuilds the wiki outline
        cache. Also installs the index_html and standard_error_message
        dtml methods. XXX split ? 

        You can set render=0 to skip the page pre-rendering part,
        completing much faster on large wikis.

        The optional batch argument forces a commit every N pages.
        This may be useful to get a complete run in large/busy wikis,
        which can be difficult due to conflict errors or memory usage.

        Requires 'Manage properties' permission on the folder.
        """
        if not self.checkPermission(Permissions.manage_properties,
                                     self.folder()):
            raise Unauthorized, (
             _('You are not authorized to upgrade all pages.') + \
             _('(folder -> Manage properties)'))
        
        batch = int(batch)
        if render: BLATHER('upgrading/reindexing/pre-rendering all pages:')
        else: BLATHER('upgrading/reindexing all pages:')
        starttime = clock()
        n, total = 0, self.pageCount()
        self.setupCatalog(reindex=0)
        self.rebuildWikiOutline()
        for p in self.pageObjects(): # poor caching (not a problem here)
            n += 1
            try:
                p.upgrade(REQUEST)
                p.upgradeId(REQUEST)
                p.fixEncoding()
                if render:
                    p.preRender(clear_cache=1)
                    msg = 'upgraded and pre-rendered page'
                else:
                    msg = 'upgraded page'
                # make sure every page is cataloged - slow but thorough
                p.index_object(log=0)
                BLATHER('%s %d/%d %s'%(msg,n,total,p.id()))
            except:
                BLATHER('failed to upgrade page %d/%d %s: %s' \
                     % (n,total,p.id(),formattedTraceback()))
            if batch and n % batch == 0:
                BLATHER('committing')
                get_transaction().commit()
        self.setupDtmlMethods()
        endtime = clock()
        BLATHER('upgrade complete, %d pages processed in %fs, %.1f pages/s' \
                %(n, endtime-starttime, n/(endtime-starttime)))

    # allow extra actions to be added to this method
    # upgradeId hooks return a page name that should be used
    # as the basis for setting the id (tracker uses this)
    global upgradeId_hooks
    upgradeId_hooks = []

    security.declareProtected(Permissions.View, 'upgradeId')
    def upgradeId(self,REQUEST=None):
        """
        Make sure a page's id conforms with its title (may also change title!)

        See also canonicalIdFrom, http://zwiki.org/HowZwikiTitleAndIdWorks .
        Does not leave a placeholder, so may break incoming links.  Does
        update backlinks, because it's less work than fixing up links by
        hand afterward. This makes it too slow to use in auto-upgrade,
        though, so people must call this manually or more usually via
        upgradeAll.

        With legacy pages (or manually renamed pages), it may happen that
        there's a clash between two similarly-named pages mapping to the
        same canonical id. In this case we just log the error and move on.

        The tracker plugin modifies this to also rename old IssueNoNNNN
        pages to the new #NNNN style.
        """
        # let plugins influence the new title & id..
        name = callHooks(upgradeId_hooks, self) or self.pageName()
        # now we can just call rename, it will do what's necessary
        try:
            self.rename(name,updatebacklinks=1,sendmail=0,REQUEST=REQUEST)
        except CopyError:
            BLATHER(
                'upgradeId for "%s" (%s) failed - does %s already exist ?' \
                % (self.pageName(),self.getId(),self.canonicalIdFrom(name)))

    def upgradePageType(self):
        """Correct any problems with this page's page type."""
        t = self.page_type
        if not t in PAGE_TYPES.keys():
            t2 = modernPageTypeFor(t)
            BLATHER("upgrading %s's page type from %s to %s" % (self.getId(),t,t2))
            self.setPageType(t2)

    # allow extra actions to be added to this method
    # upgrade hooks return non-null if the page object was changed
    # they should be fast as upgrade is called on each page view
    global upgrade_hooks
    upgrade_hooks = []

    # performance-sensitive ?
    security.declareProtected(Permissions.View, 'upgrade')
    def upgrade(self,REQUEST=None):
        """
        Upgrade an old page instance (and possibly the folder as well).

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
        # NB be a bit careful about  acquisition while doing this

        # migrate a WikiForNow _st_data attribute
        if safe_hasattr(self.aq_base, '_st_data'):
            self.raw = self._st_data
            del self._st_data
            changed = 1

        # upgrade old page types
        pagetype = self.pageTypeId()
        if pagetype in PAGE_TYPE_UPGRADES.keys():
            self.setPageType(self.modernPageTypeFor(pagetype))
            # clear render cache; don't bother prerendering just now
            self.clearCache()
            changed = 1

        # Pre-0.9.10, creation_time has been a string in custom format and
        # last_edit_time has been a DateTime. Now both are kept as
        # ISO 8601-format strings. Might not be strictly necessary to upgrade
        # in all cases.. will cause a lot of bobobase_mod_time
        # updates.. do it anyway.
        if not self.last_edit_time:
            self.last_edit_time = self.bobobase_modification_time().ISO8601()
            changed = 1
        elif type(self.last_edit_time) is not StringType:
            self.last_edit_time = self.last_edit_time.ISO8601()
            changed = 1
        elif len(self.last_edit_time) != 25:
            try: 
                if len(self.last_edit_time) == 19: # older "ISO()" format
                    # we're using the behaviour that was standard in
                    # Zope <= 2.9, where a timestamp without timezone
                    # information was assumed to be in UTC (aka GMT)
                    self.last_edit_time = \
                    DateTime(self.last_edit_time+' GMT+0').ISO8601()
                else:
                    # some other timestamp format, leave tz information
                    # untouched, or let DateTime guess at it
                    self.last_edit_time = \
                    DateTime(self.last_edit_time).ISO8601()
                changed = 1
            except DateTimeSyntaxError:
                # can't convert to ISO 8601, just leave it be
                pass

        # If no creation_time, just leave it blank for now.
        # we shouldn't find DateTimes here, but check anyway
        if not self.creation_time:
            pass
        elif type(self.creation_time) is not StringType:
            self.creation_time = self.creation_time.ISO8601()
            changed = 1
        elif len(self.creation_time) != 25:
            try: 
                if len(self.creation_time) == 19: # older "ISO()" format
                    self.creation_time = \
                    DateTime(self.creation_time+' GMT+0').ISO8601()
                else:
                    self.creation_time = \
                    DateTime(self.creation_time).ISO8601()
                changed = 1
            except DateTimeSyntaxError:
                # can't convert to ISO 8601, just leave it be
                pass

        # _wikilinks, _links and _prelinked are no longer used
        for a in (
            '_wikilinks',
            '_links',
            '_prelinked',
            ):
            if safe_hasattr(self.aq_base,a): 
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

        # ensure parents property is a list
        if self.ensureParentsPropertyIsList(): changed = 1

        # call any extra upgrade actions eg from plugins
        if callHooks(upgrade_hooks, self): changed = 1

        if changed:
            # do a commit now so the current render will have the correct
            # bobobase_modification_time for display (many headers/footers
            # still show it)
            # XXX I don't think we need to dick around with commits any more
            #get_transaction().commit()
            BLATHER('upgraded '+self.id())

        self.upgradeComments(REQUEST)
                
        # PageMailSupport does a bit more (merge here ?)
        self._upgradeSubscribers()

        # make sure there is a catalog for this wiki
        self.ensureCatalog()

        # make sure there is an up-to-date outline cache
        self.ensureWikiOutline()

    #XXX this is copied code which needs to be refactored after 0.60
    security.declareProtected('Manage properties', 'setupPages')
    def setupPages(self,REQUEST=None):
        """
        Install some default wiki pages to help get a wiki started.
        """
        # copied from ...
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
                        # XXX: this will choke if it tries to
                        # create a page with a .png file
                        self.create(name,text=text)
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.pageUrl())

    #XXX this is copied code which needs to be refactored after 0.60
    security.declareProtected('Manage properties', 'setupPages')
    def setupDtmlPages(self,REQUEST=None):
        """
        Install the DTML page implementations of some standard views.

        This facilitates easy tweaking and development.
        It doesn't check if dtml is enabled in the wiki, just
        creates the pages with the default page type.
        """
        dir = os.path.join(package_home(globals()),'skins','zwiki')
        filenames = os.listdir(dir)
        for filename in filenames:
            if filename[-5:] != '.dtml':
                pass
            else:
                m = re.search(r'(.+)\.(.+)',filename)
                if m:
                    name, type = m.group(1), m.group(2)
                    if not self.pageWithName(name):
                        text=open(os.path.join(dir,filename),'r').read()
                        # parse optional parents list
                        m = re.match(r'(?si)(^#parents:(.*?)\n)?(.*)',text)
                        if m.group(2): parents = split(strip(m.group(2)),',')
                        else: parents = []
                        text = m.group(3)
                        self.create(name,text=text)
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.pageUrl())

    security.declareProtected('Manage properties', 'setupDtmlMethods')
    def setupDtmlMethods(self,REQUEST=None):
        """
        Install some default DTML methods to make wikis work better.

        These include:
        index_html - redirects to the wiki's front page
        standard_error_message - handles 404s to enable fuzzy urls etc.

        Existing objects with the same name won't be overwritten.
        """
        d = os.path.join(package_home(globals()),'content','basic')
        dtmlmethods = [f[:-5] for f in os.listdir(d) if f.endswith('.dtml')]
        ids = self.folder().objectIds()
        for m in dtmlmethods:
            # avoid acquisition.. self.folder().aq_base won't work
            if m not in ids:
                addDTMLMethod(
                    self.folder(),
                    m,
                    title='',
                    file=open(os.path.join(d,m+'.dtml'),'r').read())
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.pageUrl())

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
            REQUEST.RESPONSE.redirect(self.pageUrl())

    security.declareProtected('Manage properties', 'setupCatalog')
    def setupCatalog(self,REQUEST=None,reindex=1):
        """
        Create and/or configure a catalog for this wiki.

        Safe to call more than once; will ignore any already existing
        items. For simplicity we install all metadata for plugins (like
        Tracker) here as well.
        """
        if self.inRevisionsFolder(): return
        if not self.hasCatalog():
            self.folder().manage_addProduct['ZCatalog'].manage_addZCatalog('Catalog','')
        catalog = self.catalog()
        catalogindexes, catalogmetadata = catalog.indexes(), catalog.schema()
        PluginIndexes = catalog.manage_addProduct['PluginIndexes']
        class Extra:
            """ Just a dummy to build records for the Lexicon."""
            pass

        if 'ZwikiLexicon' not in catalog.objectIds('ZCTextIndex Lexicon'):
            wordSplitter = Extra()
            wordSplitter.group = 'Word Splitter'
            wordSplitter.name = 'Unicode HTML aware splitter'
            caseNormalizer = Extra()
            caseNormalizer.group = 'Case Normalizer'
            caseNormalizer.name = 'Unicode Case normalizer'
            catalog.manage_addProduct['ZCTextIndex'].manage_addLexicon(
              'ZwikiLexicon', 'Lexicon', (wordSplitter, caseNormalizer))
        for i in TEXTINDEXES:
            # we use a ZCTI here and set up appropriately
            # this will always work with what stock Zope and Zwiki provides
            # admins can replace with a more potent or differently setup index
            # a TextIndex is case sensitive, exact word matches only
            # a ZCTextIndex can be case insensitive and do right-side wildcards
            # a TextIndexNG2 can be case insensitive and do both wildcards
            if not i in catalogindexes or \
            catalog._catalog.getIndex(i).meta_type == 'TextIndex':
                if i in catalogindexes: # it's there, so it's the wrong kind
                    catalog.delIndex(i)
                extra = Extra()
                extra.index_type = 'Okapi BM25 Rank'
                extra.lexicon_id = 'ZwikiLexicon'
                extra.doc_attr = i
                catalog.addIndex(i, 'ZCTextIndex', extra)

        for i in FIELDINDEXES:
            if not i in catalogindexes: PluginIndexes.manage_addFieldIndex(i)
        for i in KEYWORDINDEXES:
            if not i in catalogindexes: PluginIndexes.manage_addKeywordIndex(i)
        for i in DATEINDEXES:
            if not i in catalogindexes: PluginIndexes.manage_addDateIndex(i)
        for i in PATHINDEXES:
            if not i in catalogindexes: PluginIndexes.manage_addPathIndex(i)
        for m in PAGE_METADATA:
            if not m in catalogmetadata: catalog.manage_addColumn(m)
        if reindex:
            # now index each page, to make all indexes and metadata current
            n = 0
            cid = self.catalog().getId()
            for p in self.pageObjects():
                n = n + 1
                BLATHER('indexing page %d %s in %s'%(n,p.id(),cid))
                p.index_object(log=0)
            BLATHER('indexing complete, %d pages processed' % n)
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.pageUrl())
            
    def ensureCatalog(self):
        """
        Ensure this wiki has a zcatalog, for fast standardized searching.

        We'll create one if needed, and index all current pages. This
        could take a while (minutes) in a large wiki.
        """
        if not self.hasCatalog() and not self.inRevisionsFolder():
            BLATHER('creating catalog for wiki',self.folder().getId())
            self.setupCatalog()

    def fixAllPagesEncoding(self, REQUEST=None):
        """Fix character encoding throughout the wiki. Needed eg when
        upgrading a pre-unicode zwiki."""
        for p in self.pageObjects(): p.fixEncoding()
        if REQUEST: REQUEST.RESPONSE.redirect(REQUEST['URL1'])

    def fixEncoding(self, enc=None, REQUEST=None):
        """Try to fix character encoding problems in this page's name,
        text, or parents property.  We now store text as unicode,
        so this just tries to convert any non-unicode text to unicode
        using the standard encoding - currently utf-8, which will work for
        most zwikis.  Some (ancient) zwikis might have other encodings, so we also check
        for the common iso8859-1 encoding, or another specified with the
        enc argument. (Ideally this would fix anything without such a
        hint.)  Returns True if changes were made.
        """
        name, text, parents = self.pageName(), self.text(), self.getParents()
        if isunicode(name) and isunicode(text) and self.hasAllUnicodeParents():
            return False
        else:
            BLATHER('converting %s to unicode' % (self.pageName()))
            enc = enc or self.encoding()
            self.clearCache()
            #self.setText(self.tounicode(text,enc))
            #bypass slow prerendering for now
            self.raw = self.cleanupText(self.tounicode(text,enc))
            self.rename(self.tounicode(name,enc))
            self.convertParentsToUnicode(enc)
            REQUEST = REQUEST or getattr(self,'REQUEST',None)
            if REQUEST: REQUEST.RESPONSE.redirect(self.pageUrl())
            return True

    def hasAllUnicodeParents(self):
        return not [p for p in self.getParents() if not isunicode(p)]

    def convertParentsToUnicode(self, enc=None):
        self.setParents([self.tounicode(p,enc) for p in self.getParents()])


InitializeClass(PageAdminSupport)


# misc admin functions.. see also __init__.py
# things are here and there to avoid circular imports

def addDTMLMethod(self, id, title='', file=''):
    id=str(id)
    title=str(title)
    ob = DTMLMethod(source_string=file, __name__=id)
    ob.title = title
    username = getSecurityManager().getUser().getUserName()
    ob.manage_addLocalRoles(username, ['Owner'])
    #ob.setSubOwner('both') #?
    self._setObject(id, ob)

