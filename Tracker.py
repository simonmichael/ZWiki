# TrackerSupport mixin

from __future__ import nested_scopes
import os, string, re
from string import join, split, strip

import DocumentTemplate
from AccessControl import getSecurityManager, ClassSecurityInfo
import Permissions
from Globals import InitializeClass, package_home

from Utils import BLATHER,formattedTraceback
from Defaults import ISSUE_CATEGORIES, ISSUE_SEVERITIES, ISSUE_STATUSES, \
     ISSUE_COLOURS
from UI import DEFAULT_TEMPLATES, loadDtmlMethod, loadPageTemplate#, onlyBodyFrom

DEFAULT_TEMPLATES['issuepropertiesform'] = loadDtmlMethod('issuepropertiesformdtml')


class TrackerSupport:
    """
    This mix-in class adds some methods to ZWikiPage to facilitate
    wiki-based issue trackers.
    """
    security = ClassSecurityInfo()
    
    security.declareProtected(Permissions.View, 'issueNumberAndName')
    def pageNameFromIssueNumberAndName(self, number, name):
        """
        Generate a valid issue page name for this wiki.

        Expects number:int, name:str. This determines the naming of new
        issue pages. It should use one of the formats recognized by
        issueNumberAndName.
        """
        return 'IssueNo%04d %s' % (number,name)
        #return '%04d %s' % (number,name)
        #return '#%04d %s' % (number,name)

    security.declareProtected(Permissions.View, 'issueNumberAndNameFrom')
    def issueNumberAndNameFrom(self, pagename):
        """
        Extract issue number and issue name from a page name if possible.

        If pagename matches one of these formats, where NNNN is one or
        more digits and ISSUENAME is any text:

         IssueNoNNNN ISSUENAME
         #NNNN ISSUENAME

        we return (NNNN, ISSUENAME), otherwise None. ISSUENAME is stripped
        of surrounding whitespace.
        """
        m = (re.match(r'(?s)^IssueNo([0-9]+)(.*)',pagename) # IssueNoNNNN...
             or re.match(r'(?s)^#([0-9]+)(.*)',pagename))   # or #NNNN...
        if m: return (int(m.group(1)), m.group(2).strip())
        else: return None

    security.declareProtected(Permissions.View, 'issueNumberAndName')
    def issueNumberAndName(self, pagename=None):
        """
        Return the issue number and name parts from this page's name if possible.
        """
        return self.issueNumberAndNameFrom(self.pageName())

    security.declareProtected(Permissions.View, 'issueNumber')
    def issueNumber(self, pagename=None):
        """
        Return this page's (or another's) issue number, or None.
        """
        tuple = self.issueNumberAndName(pagename or self.pageName())
        return tuple and tuple[0]

    security.declareProtected(Permissions.View, 'issueName')
    def issueName(self, pagename=None):
        """
        Return this page's issue name (page name without the number), or None.
        """
        tuple = self.issueNumberAndName(pagename or self.pageName())
        return tuple and tuple[1]

    security.declareProtected(Permissions.View, 'isIssue')
    def isIssue(self,pagename=None):
        """
        Does this page (or the specified page name) represent a tracker issue ?

        If we are able to extract an issue number and name from the page
        name, yes.
        """
        return self.issueNumberAndName(pagename or self.pageName()) and 1

    security.declareProtected(Permissions.View, 'issueCount')
    def issueCount(self):
        return len(filter(lambda x:x[:7]=='IssueNo',self.pageIds()))

    security.declareProtected(Permissions.View, 'hasIssues')
    def hasIssues(self): # likely.
        return self.issueCount() > 0

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
    
    security.declareProtected(Permissions.Add, 'createIssue')
    def createIssue(self, pageid='', text='', title=None,
                    category='', severity='', status='', REQUEST=None):
        """
        Convenience method for creating an issue page.

        Security notes: create will check for page creation permission.
        Sets title/category/severity/status properties without requiring
        Manage properties permission.

        XXX only old issue tracker dtml pages call this, AFAIK.  
        Clean up args. pageid is really pagename.  title is not used.

        We will try to place the issue under a suitable parent - the
        IssueTracker page if it exists, or at the top level to avoid
        having issues scattered everywhere. Better ideas ?
        """
        # XXX hardcoded.. cf trackerUrl
        if self.pageWithName('IssueTracker'): parents = ['IssueTracker']
        else: parents = []
        self.create(pageid,text=text,REQUEST=REQUEST,parents=parents)
        issue = self.pageWithName(pageid)
        issue.manage_addProperty('category','issue_categories','selection')
        issue.manage_addProperty('severity','issue_severities','selection')
        issue.manage_addProperty('status','issue_statuses','selection')
        issue.manage_changeProperties(title=pageid,
                                      category=category,
                                      severity=severity,
                                      status=status
                                      )
        self.reindex_object()

    security.declareProtected(Permissions.Add, 'createNextIssue')
    def createNextIssue(self,name='',text='',category='',severity='',status='',
                        REQUEST=None):
        """
        Create a new issue page, using the next available issue number.
        """
        issues = self.pages(isIssue=1,sort_on='id')
        if issues:
            lastnumber = self.issueNumber(issues[-1].Title)
            newnumber = lastnumber + 1
        else:
            newnumber = 1
        pagename=self.pageNameFromIssueNumberAndName(newnumber,name)
        return self.createIssue(pagename, text, None, 
                                category, severity, status, REQUEST)
    
            

    security.declareProtected(Permissions.Edit, 'changeIssueProperties')
    def changeIssueProperties(self, name=None, category=None, severity=None, 
                              status=None, log=None, REQUEST=None):
        """
        Change an issue page's properties and redirect back there.

        Also, add a comment to the page describing what was done.

        name is the issue name excluding the issue number. Changing this
        will trigger a page rename, which may be slow.
        
        Security: allows modification of some properties
        (title/category/severity/status) with zwiki edit permission rather
        than zope Manage properties permission.

        Upgrade issue: calling this before upgrading an issue to a
        0.17-style page id will mess up the id/title.
        """
        comment = ''
        if name:
            if name != self.issueName():
                newpagename = self.pageNameFromIssueNumberAndName(
                    self.issueNumber(),
                    name)
                comment += "Name: '%s' => '%s' \n" % (self.pageName(),
                                                      newpagename)
                self.rename(newpagename, updatebacklinks=1, sendmail=0,
                            REQUEST=REQUEST)
        if category:
            if category != self.category:
                comment += "Category: %s => %s \n" % (self.category,category)
                self.manage_changeProperties(category=category)
        if severity:
            if severity != self.severity:
                comment += "Severity: %s => %s \n" % (self.severity,severity)
                self.manage_changeProperties(severity=severity)
        if status:
            if status != self.status:
                comment += "Status: %s => %s \n" % (self.status,status)
                self.manage_changeProperties(status=status)
        log = log or 'property change'
        self.comment(text=comment, subject_heading=log, REQUEST=REQUEST)
        self.setLastEditor(REQUEST)
        self.reindex_object()
        if REQUEST: REQUEST.RESPONSE.redirect(self.page_url())

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

    security.declareProtected(Permissions.View, 'issuepropertiesform')
    def issuepropertiesform(self, REQUEST=None):
        """
        Render the issue properties form as a (customizable) HTML fragment.
        """
        #return onlyBodyFrom(
        return self.getSkinTemplate('issuepropertiesform')(self,REQUEST)

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
        self.upgradeFolderIssueProperties()
        # dtml pages,
        if pages:
            dir = package_home(globals())+os.sep+'content'+os.sep+'tracker'+os.sep
            for page in ['IssueTracker','FilterIssues']:
                if not self.pageWithName(page):
                    self.create(page,text=open(dir+page+'.stxdtml','r').read())
            # also, disable subtopics display under IssueTracker
            self.IssueTracker.setSubtopicsPropertyStatus(0)
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

InitializeClass(TrackerSupport)
