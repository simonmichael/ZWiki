# PluginTracker mixin

from __future__ import nested_scopes
import os, string, re, os.path
from string import join, split, strip
from types import *

import DocumentTemplate
from AccessControl import getSecurityManager, ClassSecurityInfo
from Globals import InitializeClass, package_home

from Products.ZWiki.plugins import registerPlugin
from Products.ZWiki.Defaults import registerPageMetaData
from Products.ZWiki import Permissions
from Products.ZWiki.Utils import BLATHER, formattedTraceback, addHook
from Products.ZWiki.Views import loadDtmlMethod, loadPageTemplate, TEMPLATES
     
from Products.ZWiki.I18n import _

TEMPLATES.update({
    'issuepropertiesform': loadDtmlMethod('issuepropertiesform','plugins/tracker'),
    # page template wrappers
    'issuetracker'       : loadPageTemplate('issuetracker','plugins/tracker'),
    'issuebrowser'       : loadPageTemplate('issuebrowser','plugins/tracker'),
    'filterissues'       : loadPageTemplate('filterissues','plugins/tracker'),
    # the DTML implementations
    'IssueTracker'       : loadDtmlMethod('IssueTracker','plugins/tracker'),
    'IssueBrowser'       : loadDtmlMethod('IssueBrowser','plugins/tracker'),
    'FilterIssues'       : loadDtmlMethod('FilterIssues','plugins/tracker'),
    })

# issue tracker defaults, will be installed as folder properties
ISSUE_CATEGORIES = [
    'general',
    ]
ISSUE_SEVERITIES = [
    'critical',
    'serious',
    'normal',
    'minor',
    'wishlist',
    ]
ISSUE_STATUSES = [
    'open',
    'pending',
    'closed',
    ]
# this is a list of strings like 'category,status,severity,colour' any of
# which may be empty (a wildcard). The first entry matching the issue
# will be used.
ISSUE_COLOURS = [
    ',open,critical ,#ff2222',
    ',open,serious  ,#ff9090',
    ',open,normal   ,#ffbbbb',
    ',open,minor    ,#ffdddd',
    ',open,wishlist ,#e0e0e0',
    ',open,         ,#ffe0e0',
    ',pending,      ,#ffcc77',
    ',closed,       ,#bbeebb',
    ',,             ,',
    ]

TRACKER_METADATA = [
    'category',
    'category_index',
    'severity',
    'severity_index',
    'status',
    'status_index',
    'issueColour',
    ]
for a in TRACKER_METADATA: registerPageMetaData(a)


class PluginTracker:
    """
    This mix-in class adds some methods to ZWikiPage to facilitate
    wiki-based issue trackers.
    """
    security = ClassSecurityInfo()
    
    security.declareProtected(Permissions.View, 'hasIssues')
    def hasIssues(self): # likely.
        """
        True if this wiki has any issue pages.
        """
        return self.issueCount() > 0

    security.declareProtected(Permissions.View, 'issueCount')
    def issueCount(self):
        """
        The number of issue pages in this wiki.
        """
        return len(filter(lambda x:self.isIssue(x),self.pageNames()))

    security.declareProtected(Permissions.View, 'isIssue')
    def isIssue(self,pagename=None):
        """
        True if this page (or another named page) represents a tracker issue.
        """
        return (
            self.issueNumberFrom(pagename or self.pageName()) or
            hasattr(self.aq_base,'status')
            ) and 1
            #hasattr(getattr(self,'aq_base',self),'status') if tests break

    security.declareProtected(Permissions.View, 'issueNumber')
    def issueNumber(self):
        """
        This page's issue number, or None.
        """
        numberandname = self.issueNumberAndNameFrom(self.pageName())
        return numberandname and numberandname[0]

    security.declareProtected(Permissions.View, 'issueName')
    def issueName(self):
        """
        This page's issue name (the non-number part), or None.
        """
        numberandname = self.issueNumberAndNameFrom(self.pageName())
        return numberandname and numberandname[1]

    security.declareProtected(Permissions.View, 'issueNumberFrom')
    def issueNumberFrom(self, pagename):
        """
        Extract the issue number from a page name, or None.
        """
        numberandname = self.issueNumberAndNameFrom(pagename)
        return numberandname and numberandname[0]

    security.declareProtected(Permissions.View, 'issueNameFrom')
    def issueNameFrom(self, pagename):
        """
        Extract the issue name part from a page name, or None.
        """
        numberandname = self.issueNumberAndNameFrom(pagename)
        return numberandname and numberandname[1]

    def shortIssueNamesEnabled(self):
        """Should issue page names start with just # in this wiki ?"""
        return 1 #return getattr(self.folder(),'short_issue_names',1) and 1

    security.declareProtected(Permissions.View, 'issueNumberAndNameFrom')
    def issueNumberAndNameFrom(self, pagename):
        """
        Extract issue number and issue name from a page name if possible.

        Returns a tuple of (issuenumber, issuename) strings, or (None,
        pagename) if no issue number can be found. The issue name is
        stripped of surrounding whitespace.

        Should be able to parse the format generated by
        pageNameFromIssueNumberAndName, and other common formats for
        compatibility For example:

         IssueNoN ISSUENAME
         IssueNoN

        and when short_issue_names is enabled:
        
         #N ISSUENAME
         #N

        where N is one or more digits and ISSUENAME is any text.
        """
        m = (re.match(r'(?s)^IssueNo([0-9]+)(.*)',pagename) or
             (self.shortIssueNamesEnabled() and
              re.match(r'(?s)^#([0-9]+)(.*)',pagename)))
        if m: return (int(m.group(1)), m.group(2).strip())
        else: return (None,pagename.strip())

    security.declareProtected(Permissions.View, 'pageNameFromIssueNumberAndName')
    def pageNameFromIssueNumberAndName(self, number, name):
        """
        Make a page name from an issue number and issue name.

        This method controls the naming of new issue pages.  There are
        currently two variants, controlled by the short_issue_names folder
        property.  It should be parseable by issueNumberAndNameFrom.
        Expects number:int, name:str.
        """
        if self.shortIssueNamesEnabled():
            return self.shortIssueNameFrom(number,name)
        else:
            return self.longIssueNameFrom(number,name)

    security.declareProtected(Permissions.View, 'issuePageWithNumber')
    def issuePageWithNumber(self, number):
        """
        Return the issue page with the specified issue number, or None.

        Tries both the short and long issue page name formats;
        should match issueNumberAndNameFrom.
        It's harmless to call this with a non-number.
        """
        if type(number) != IntType: return None
        return (
            self.pageWithFuzzyName(self.shortIssueNameFrom(number),
                                   allow_partial=1,
                                   numeric_match=1) or
            self.pageWithFuzzyName(self.longIssueNameFrom(number),
                                   allow_partial=1,
                                   numeric_match=1))

    def shortIssueNameFrom(self, number, name=''):
        """
        Make up an issue page name from the issue number & description.

        (name here means the text part, ie the issue description).

        If number is None, just returns name unchanged.
        """
        if number != None:
            return '#%d %s' % (number,name)
        else:
            return name

    def longIssueNameFrom(self, number, name=''):
        return 'IssueNo%04d %s' % (number,name)

    security.declareProtected(Permissions.Add, 'createIssue')
    def createIssue(self, pageid='', text='', title=None,
                    category='', severity='', status='', REQUEST=None,
                    sendmail=1):
        """
        Create a page representing an issue with the specified details.

        Security notes: sets title/category/severity/status properties
        without requiring Manage properties permission.
        create() will also check the edits_need_username property and
        redirect us to /denied if appropriate.

        We try to place the issue under a suitable parent - the
        IssueTracker page if it exists, or at the top level to avoid
        having issues scattered everywhere. Better ideas ?

        Returns the new page name or None.

        XXX clean up old args kept for backwards compatibility. Only
        really old issue tracker dtml pages call this directly.
        pageid is really pagename.  title is not used.
        """
        # XXX hardcoded.. cf trackerUrl
        if self.pageWithName('IssueTracker'): parents = ['IssueTracker']
        else: parents = []
        # might fail due to edits_need_username
        name = self.create(pageid,text=text,REQUEST=REQUEST,parents=parents,
                           sendmail=sendmail)
        if name:
            issue = self.pageWithName(pageid)
            issue.manage_addProperty('category','issue_categories','selection')
            issue.manage_addProperty('severity','issue_severities','selection')
            issue.manage_addProperty('status','issue_statuses','selection')
            issue.manage_changeProperties(title=pageid,
                                          category=category,
                                          severity=severity,
                                          status=status
                                          )
            #self.index_object() # XXX why ??
            return name
        else:
            return None

    security.declareProtected(Permissions.Add, 'createNextIssue')
    def createNextIssue(self,name='',text='',category='',severity='',status='',
                        REQUEST=None,sendmail=1):
        """
        Add a new issue page, using the next available number, and redirect.

        createIssue() (really create()) will also check the
        edits_need_username property and may redirect to an error.
        Otherwise this will redirect to the tracker url (when called
        via the web). Returns the new page's name or None.
        """
        newnumber = self.nextIssueNumber(REQUEST=REQUEST)
        pagename=self.pageNameFromIssueNumberAndName(newnumber,name)
        pagename=self.createIssue(pagename,text,None, 
                                  category,severity,status,REQUEST,sendmail)
        if pagename:
            if REQUEST:
                REQUEST.RESPONSE.redirect(self.trackerUrl())
        return pagename

    security.declareProtected(Permissions.View, 'nextIssueNumber')
    def nextIssueNumber(self, REQUEST=None):
        """
        Get the next available issue number.

        Adds one to the current highest issue number, so gaps are allowed.
        Handles both old and new-style issue page names.
        
        Does a catalog search, so REQUEST may be required to authenticate
        and get the proper results. I think.
        """
        issuenumbers = [self.issueNumberFrom(b.Title) for b in \
                        self.pages(isIssue=1,REQUEST=REQUEST)]
        issuenumbers.sort()
        return (([0]+issuenumbers)[-1]) + 1

    security.declareProtected(Permissions.Edit, 'changeIssueProperties')
    def changeIssueProperties(self, name=None, category=None, severity=None, 
                              status=None, log=None, text='', REQUEST=None):
        """
        Change an issue page's properties and redirect back there.

        Also, add a comment to the page describing what was done.
        Optionally a comment subject and body can be set.

        name is the issue name excluding the issue number. Changing this
        will trigger a page rename, which may be slow.
        
        Security: allows modification of some properties
        (title/category/severity/status) with zwiki edit permission rather
        than zope Manage properties permission.

        Upgrade issue: calling this before upgrading an issue to a
        0.17-style page id will mess up the id/title.
        """
        if not self.checkSufficientId(REQUEST):
            return self.denied(
                _("Sorry, this wiki doesn't allow anonymous edits. Please configure a username in options first."))

        comment = ''
        if name:
            if name != self.issueName():
                newpagename = self.pageNameFromIssueNumberAndName(
                    self.issueNumber(),
                    name)
                comment += "Name: '%s' => '%s' \n" % (self.pageName(),
                                                      newpagename)
                if not self.checkPermission(Permissions.Rename, self):
                    raise 'Unauthorized', (_('You are not authorized to rename this ZWiki Page.'))
                self.rename(newpagename, updatebacklinks=1, sendmail=0,
                            REQUEST=REQUEST)
 
        if category:
            old = getattr(self,'category','')
            if category != old:
                comment += "Category: %s => %s \n" % (old,category)
                if not self.checkPermission(Permissions.Edit, self):
                    raise 'Unauthorized', (_('You are not authorized to edit this ZWiki Page.'))
                self.manage_changeProperties(category=category)
        if severity:
            old = getattr(self,'severity','')
            if severity != old:
                comment += "Severity: %s => %s \n" % (old,severity)
                if not self.checkPermission(Permissions.Edit, self):
                    raise 'Unauthorized', (_('You are not authorized to edit this ZWiki Page.'))
                self.manage_changeProperties(severity=severity)
        if status:
            old = getattr(self,'status','')
            if status != old:
                comment += "Status: %s => %s \n" % (old,status)
                if not self.checkPermission(Permissions.Edit, self):
                    raise 'Unauthorized', (_('You are not authorized to edit this ZWiki Page.'))
                self.manage_changeProperties(status=status)
        if text:
            comment += '\n' + text

        if comment:
            if not self.checkPermission(Permissions.Comment, self):
                raise 'Unauthorized', (_('You are not authorized to comment on this ZWiki Page.'))
            # there was a change, note it on the page and via mail
            # fine detail: don't say (property change) if there wasn't
            subject = ''
            if log: subject += log
            #if '=>' in comment: subject += ' (%s)' % _('property change')
            self.comment(
                text=comment,
                subject_heading=subject,
                REQUEST=REQUEST)
            # comment takes care of this I believe
            #self.setLastEditor(REQUEST)
            #self.reindex_object()
        if REQUEST:
            REQUEST.RESPONSE.redirect(self.pageUrl())

    def category_index(self):
        """helper method to facilitate sorting catalog results"""
        try:
            return 1 + list(self.issue_categories).index(self.category)
        except (AttributeError,ValueError):
            return 0
        
    def severity_index(self):
        """helper method to facilitate sorting catalog results"""
        try:
            return 1 + list(self.issue_severities).index(self.severity)
        except (AttributeError,ValueError):
            return 0

    def status_index(self):
        """helper method to facilitate sorting catalog results"""
        try:
            return 1 + list(self.issue_statuses).index(self.status)
        except (AttributeError,ValueError):
            return 0

    # UI methods

    security.declareProtected(Permissions.View, 'issuetracker')
    def issuetracker(self, REQUEST=None):
        """
        Render the issuetracker form (template-customizable).
        """
        return self.getSkinTemplate('issuetracker')(self,REQUEST)

    security.declareProtected(Permissions.View, 'filterissues')
    def filterissues(self, REQUEST=None):
        """
        Render the filterissues form (template-customizable).
        """
        return self.getSkinTemplate('filterissues')(self,REQUEST)

    security.declareProtected(Permissions.View, 'issuebrowser')
    def issuebrowser(self, REQUEST=None):
        """
        Render the issuebrowser form (template-customizable).
        """
        return self.getSkinTemplate('issuebrowser')(self,REQUEST)

    security.declareProtected(Permissions.View, 'addIssueFormTo')
    def addIssueFormTo(self,body):
        """
        Add an issue property form above the rendered page text.
        """
        REQUEST = getattr(self,'REQUEST',None)
        return self.stxToHtml(self.issuepropertiesform(REQUEST=REQUEST)) + body
            
    security.declareProtected(Permissions.View, 'issueColour')
    def issueColour(self):
        """
        Tell the appropriate issue colour for this page.
        """
        # don't acquire these
        return self.issueColourFor(
            getattr(getattr(self,'aq_base',self),'category',''),
            getattr(getattr(self,'aq_base',self),'severity',''),
            getattr(getattr(self,'aq_base',self),'status',''),
            )

    security.declareProtected(Permissions.View, 'issueColourFor')
    def issueColourFor(self, category='', severity='', status=''):
        """
        Choose an issue colour based on issue properties.

        Finds the best match in a list of strings like
        "category,status,severity,colour", any of which may be empty.  The
        defaults can be overridden with an 'issue_colours' folder lines
        property.

        If no match is found in the colour list, returns the empty string.
        """
        category, status, severity = map(lambda x:x.strip(),
                                         (category, status, severity))
        # can't figure out a reasonable way to do this without python 2.1
        # convert the strings into dictionaries
        colours = getattr(self.folder(),'issue_colours',ISSUE_COLOURS)
        colours = filter(lambda x:x.strip(),colours)
        l = []
        for i in colours:
            a, b, c, d = map(lambda x:x.strip(),i.split(','))
            l.append({
                'category':a,
                'status':b,
                'severity':c,
                'colour':d,
                })
        # find the most specific match
        l = l and (filter(lambda x:x['category']==category, l) or
                   filter(lambda x:x['category']=='', l))
        l = l and (filter(lambda x:x['status']==status, l) or
                   filter(lambda x:x['status']=='', l))
        l = l and (filter(lambda x:x['severity']==severity, l) or
                   filter(lambda x:x['severity']=='', l))
        if not l:
            return ''
        else:
            return l[0]['colour']
    
    security.declareProtected(Permissions.View, 'issuepropertiesform')
    def issuepropertiesform(self, REQUEST=None):
        """
        Render the issue properties form as a (customizable) HTML fragment.
        """
        return self.getSkinTemplate('issuepropertiesform')(self,REQUEST)

    security.declareProtected(Permissions.View, 'trackerUrl')
    def trackerUrl(self):
        return self.urlForDtmlPageOrMethod('IssueTracker','issuetracker')

    security.declareProtected(Permissions.View, 'filterUrl')
    def filterUrl(self):
        return self.urlForDtmlPageOrMethod('FilterIssues','filterissues')

    security.declareProtected(Permissions.View, 'filterUrl')
    def issueBrowserUrl(self):
        return self.urlForDtmlPageOrMethod('IssueBrowser','issuebrowser')

    # setup methods

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
        items.  
        """
        TextIndexes = [
            ]
        FieldIndexes = [
            'category',
            'category_index',
            'isIssue',
            'issueNumber',
            'severity',
            'severity_index',
            'status',
            'status_index',
            'issueName']
        KeywordIndexes = [
            ]
        DateIndexes = [
            ]
        PathIndexes = [
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
        # setupCatalog just does this by default now, since
        # ensureCompleteMetadataIn always tries to fetch all metadata
        #for m in TRACKER_METADATA:
        #    if not m in catalogmetadata: catalog.manage_addColumn(m)
        # properties,
        self.upgradeFolderIssueProperties()
        # dtml pages,
        if pages:
            dir = package_home(globals())
            for page in ['IssueTracker','FilterIssues','IssueBrowser']:
                if not self.pageWithName(page):
                    self.create(page,
                                text=open(os.path.join(dir,page+'.dtml'),'r').read(),
                                sendmail=0,
                                type='stx')

            # also, disable subtopics display under IssueTracker
            self.IssueTracker.setSubtopicsPropertyStatus(0)

        # index each page, to make all indexes and metadata current
        # may duplicate some work in setupCatalog
        n = 0
        cid = self.catalog().getId()
        for p in self.pageObjects():
            n = n + 1
            BLATHER('indexing page #%d %s in %s'%(n,p.id(),cid))
            p.index_object(log=0)
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

    def upgradeFolderIssueProperties(self):
        """
        Upgrade issue tracker related properties on the wiki folder if needed.

        Currently just adds properties if missing.
        """
        folder = self.folder()
        existingprops = map(lambda x:x['id'], folder._properties)
        for prop, values in [
            ['issue_categories',ISSUE_CATEGORIES],
            ['issue_severities',ISSUE_SEVERITIES],
            ['issue_statuses',ISSUE_STATUSES],
            ['issue_colours',ISSUE_COLOURS],
            ]:
            if not prop in existingprops:
                folder.manage_addProperty(prop,join(values,'\n'),'lines')
                    
    def upgradeIssueProperties(self):
        """
        Upgrade tracker related properties on this page (and folder) if needed.

        Returns non-zero if we changed any page properties, to help
        upgrade() efficiency.
        """
        changed = 0
        if self.isIssue():
            # check folder first so our selection properties will work
            self.upgradeFolderIssueProperties()
            
            existingprops = map(lambda x:x['id'], self._properties)
            for prop, values, default in [
                ['category','issue_categories',None],
                ['severity','issue_severities','normal'],
                ['status','issue_statuses',None],
                ]:
                if not prop in existingprops:
                    self.manage_addProperty(prop,values,'selection')
                    if default: setattr(self,prop,default)
                    changed = 1

        return changed

InitializeClass(PluginTracker)
registerPlugin(PluginTracker)

# register some upgrade hooks
from Products.ZWiki.Admin import upgrade_hooks, upgradeId_hooks

# install issue properties if missing, eg if this page is being
# viewed as an issue for the first time
addHook(upgrade_hooks, PluginTracker.upgradeIssueProperties)

# convert old-style IssueNNNN ... page names to #NNNN ...
# when checking page id. Leaves non-issue page names unchanged.
addHook(upgradeId_hooks,
        lambda self:
        self.pageNameFromIssueNumberAndName(self.issueNumber(),
                                            self.issueName()))
