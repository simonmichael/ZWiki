# UI-related methods
#
# Here we emulate CMF skins for a limited set of skin templates with known
# names (wikipage, editform, backlinks etc): if they're in the zodb, use
# them, if not get defaults from the filesystem. To make this work in any
# Folder, wiki pages have methods of those names (below) which invoke the
# appropriate templates. From 0.25, we still support this for backwards
# compatibility but prefer to use the CMF-style SkinnedFolder whenever
# possible, eg with new wikis.  So outside of CMF, templates are found thus:
#
#  1. (if there's a method of that name (below), call it; it will..)
#  2. look in the wiki folder
#  3. in a SkinnedFolder, look in the user's skin (one or more layers in skins/)
#  4. look in the parent folders, up to the root folder (acquisition)
#  5. (if we are in a method from step 1 and no template was found,
#     get it from ZWiki/skins/default on the filesystem)
#
# Skin templates may be either page templates or DTML methods, again for
# backwards compatibility.

from __future__ import nested_scopes
import os, sys, re, string, time, math
import string
from string import split,join,find,lower,rfind,atoi,strip

from App.Common import rfc1123_date
from AccessControl import getSecurityManager, ClassSecurityInfo
import Permissions
import Globals
from Globals import MessageDialog, HTMLFile, DTMLFile
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS.Image import File
from Products.PageTemplates.Expressions import SecureModuleImporter

from Defaults import PAGE_METATYPE
from Utils import BLATHER,formattedTraceback
from LocalizerSupport import _, N_

# built-in defaults for skin objects
def defaultPageTemplate(name):
    # hack PageTemplateFile templates to see the folder as their container,
    # like their zodb counterparts do. Some simpler way to do this ?
    class MyPTFile(PageTemplateFile):
        def pt_getContext(self):
            root = self.getPhysicalRoot()
            c = {'template': self,
                 'here': self.aq_inner.aq_parent,
                 'container': self.aq_inner.aq_parent.aq_parent,
                 'nothing': None,
                 'options': {},
                 'root': root,
                 'request': getattr(root, 'REQUEST', None),
                 'modules': SecureModuleImporter,
                 }
            return c
    pt = MyPTFile('skins/default/%s.pt'%name, globals(), __name__=name)
    pt._cook_check() # ensure _text is there, we peek at it below    
    return pt
def defaultDtmlMethod(name):
    return HTMLFile('skins/default/%s'%name, globals())
def defaultStylesheet(name):
    thisdir = os.path.split(os.path.abspath(__file__))[0]
    filepath = os.path.join(thisdir,'skins/default',name)
    data,mtime = '',0
    try:
        fp = open(filepath,'rb')
        data = fp.read()
        mtime = os.path.getmtime(filepath)
    finally: fp.close()
    file = File('stylesheet','',data,content_type='text/css')
    # fix b_m_t which will otherwise be current time
    # why doesn't that lambda need a self argument ?
    file.bobobase_modification_time = lambda:mtime
    return file

# the basic skin templates
default_wikipage = defaultPageTemplate('wikipage')
default_wikipage_macros = defaultPageTemplate('wikipage_macros')
default_stylesheet = defaultStylesheet('stylesheet.css')
default_backlinks = defaultPageTemplate('backlinks')
default_contentspage = defaultPageTemplate('contentspage')
default_diffform = defaultPageTemplate('diffform')
default_editform = defaultPageTemplate('editform')
default_subscribeform = defaultPageTemplate('subscribeform')
# these include a chunk of DTML for easier syncing with the page-based
# implementations:
default_recentchanges = defaultPageTemplate('recentchanges')
default_recentchangesdtml = defaultDtmlMethod('recentchangesdtml')
default_searchwiki = defaultPageTemplate('searchwiki')
default_searchwikidtml = defaultDtmlMethod('searchwikidtml')
default_useroptions = defaultPageTemplate('useroptions')
default_useroptionsdtml = defaultDtmlMethod('useroptionsdtml')
default_issuetracker = defaultPageTemplate('issuetracker')
default_issuetrackerdtml = defaultDtmlMethod('issuetrackerdtml')
default_filterissues = defaultPageTemplate('filterissues')
default_filterissuesdtml = defaultDtmlMethod('filterissuesdtml')

def isPageTemplate(obj):
    return getattr(obj,'meta_type',None) in (
        'Page Template',            # template found in wiki folder or above
        'Filesystem Page Template', # default template in CMF skin/SkinnedFolder
        'Page Template (File)',     # default from filesystem
        )
def isDtmlMethod(obj):
    return getattr(obj,'meta_type',None) in (
        'DTML Method', 
        'Filesystem DTML Method',
        'DTML Method (File)',
        'DTML Document', 
        'Filesystem DTML Document',
        'DTML Document (File)',
        )
def isFile(obj):
    return getattr(obj,'meta_type',None) in (
        'File',
        )
def isZwikiPage(obj):
    return getattr(obj,'meta_type',None) in (
        PAGE_METATYPE,
        )


class UI:
    # see above
    """ 
    A CMF/non-CMF skinning mechanism and UI-related methods for ZWikiPage.

    This provides a small number of well-known methods - editform,
    backlinks etc. - which render an appropriate view based on templates
    (Page Templates or DTML Methods) in the CMF skin, in the wiki folder
    or above, or built-in defaults.

    To facilitate troubleshooting and bug reporting, template errors are
    caught and a traceback and some attempt at a useful error message are
    displayed (this sometimes hinders debugging though).

    XXX cleanup ongoing
    XXX simplify/update/improve error messages
    """
    security = ClassSecurityInfo()

    # XXX kludge: wikipage usually gets called by addStandardLayout, not
    # directly; but provide this so you can configure it as the "view"
    # method in portal_types -> Wiki Page -> actions to force the use of
    # Zwiki's non-CMF skin inside CMF
    security.declareProtected(Permissions.View, 'wikipage')
    def wikipage(self, dummy=None, REQUEST=None, RESPONSE=None):
        """
        Display the default or custom page view.
                    
        May be overridden by a page template or DTML method of the same name.
        """
        form = getattr(self.folder(),'wikipage',default_wikipage)
        if isPageTemplate(form):
            return form.__of__(self)(self,REQUEST,body=self.render()) #XXX temporary kludge!
        elif isDtmlMethod(form):
            return form(self,REQUEST)
        else:
            return "<html><body>This wiki's custom wikipage template is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"
           
    security.declareProtected(Permissions.View, 'addSkinTo')
    def addSkinTo(self,body,**kw):
        """
        Add the standard wiki page skin to the rendered page body.

        If a "bare" keyword is found in REQUEST, or if we are in a CMF
        site, do nothing. Otherwise,
        
        1. if a wikipage page template is found in this folder or above,
        use that

        2. if we are in a SkinnedFolder, look in the current skin

        3. if a standard_wiki_header or standard_wiki_footer dtml method
        is found, use them (legacy support). If only one is found, show a
        warning for the other.
        
        4. otherwise, use default_wikipage (skins/default/wikipage.pt).

        """
        # CMF will do it's own skinning
        if self.supportsCMF() and self.inCMF(): return body
        # bare keyword disables skin
        REQUEST = getattr(self,'REQUEST',None)
        if hasattr(REQUEST,'bare') or kw.has_key('bare'): return body

        folder = self.folder()
        if hasattr(folder,'wikipage') and isPageTemplate(folder.wikipage):
            return folder.wikipage.__of__(self)(self,REQUEST,body=body,**kw)
                
        elif ((hasattr(folder,'standard_wiki_header') and
               isDtmlMethod(folder.standard_wiki_header)) or
              (hasattr(folder,'standard_wiki_footer') and
               isDtmlMethod(folder.standard_wiki_footer))):
            return self.standard_wiki_header(REQUEST) + \
                   body + \
                   self.standard_wiki_footer(REQUEST)
        else:
            return default_wikipage.__of__(self)(self,REQUEST,body=body,**kw)

    security.declareProtected(Permissions.View, 'wikipage_macros')
    def wikipage_macros(self, REQUEST=None):
        """
        Return the default or customized macros used by the wikipage template.
                    
        May be overridden by a page template of the same name.
        """
        pt = getattr(self.folder(),'wikipage_macros',default_wikipage_macros)
        # this is a helper template - don't evaluate it here, just hand it over
        return pt.__of__(self)
           
    security.declareProtected(Permissions.View, 'stylesheet')
    def stylesheet(self, REQUEST=None):
        """
        Return a default or custom style sheet for use by the other templates.

        The default skin links to this method instead of to a stylesheet
        directly, so that a default stylesheet can be provided.  It may be
        overridden with an object named stylesheet or stylesheet.css.
        This is usually a File, but can also be a page template or dtml
        method.

        In the latter case, the (dynamic) stylesheet will have no
        last-modified header and browsers will reload it for each page
        view. Note even a File or the default stylesheet will get loaded
        at least once per page, since the default skin links here with a
        per-page url.
        XXX can we do better ? always inline the stylesheet ?
        
        """
        if REQUEST: REQUEST.RESPONSE.setHeader('Content-Type', 'text/css')
        form = getattr(self.folder(),'stylesheet',
                       getattr(self.folder(),'stylesheet.css',
                               default_stylesheet
                               ))
        if isPageTemplate(form) or isDtmlMethod(form):
            return form.__of__(self)(self,REQUEST)
        else: # a File
            if REQUEST:
                modified = form.bobobase_modification_time()
                REQUEST.RESPONSE.setHeader('Last-Modified',
                                           rfc1123_date(modified))
            return form.index_html(REQUEST,REQUEST.RESPONSE)
           
    security.declareProtected(Permissions.View, 'standard_wiki_header')
    def standard_wiki_header(self, REQUEST=None):
        """
        Return the custom standard_wiki_header or a default with warning.
        """
        if (hasattr(self.folder(),'standard_wiki_header') and
            isDtmlMethod(self.folder().standard_wiki_header)):
            return self.folder().standard_wiki_header(self,REQUEST)
        else:
            return '<html>\n<body>\nThis wiki has a custom standard_wiki_footer but no corresponding standard_wiki_header. Suggestion: remove it.\n'

    security.declareProtected(Permissions.View, 'standard_wiki_footer')
    def standard_wiki_footer(self, REQUEST=None):
        """
        Return the custom standard_wiki_footer or a default with warning.
        """
        if (hasattr(self.folder(),'standard_wiki_footer') and
            isDtmlMethod(self.folder().standard_wiki_footer)):
            return self.folder().standard_wiki_footer(self,REQUEST)
        else:
            return '<p>This wiki has a custom standard_wiki_header but no corresponding standard_wiki_footer. Suggestion: remove it.</body></html>'

    security.declareProtected(Permissions.View, 'backlinks')
    def backlinks(self, REQUEST=None):
        """
        Display a default or custom backlinks page. 

        May be overridden by a page template or DTML method of the same
        name.
        """
        form = getattr(self.folder(),'backlinks',default_backlinks)
        if isPageTemplate(form) or isDtmlMethod(form):
            return form.__of__(self)(self,REQUEST)
        else:
            return "<html><body>This wiki's custom backlinks is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    security.declareProtected(Permissions.View, 'contentspage')
    def contentspage(self, hierarchy, singletons, REQUEST=None):
        """
        Display a default or custom contents page. 

        May be overridden by a page template or DTML method of the same
        name.
        """
        form = getattr(self.folder(),'contentspage',default_contentspage)
        if isPageTemplate(form) or isDtmlMethod(form):
            return form.__of__(self)(self,REQUEST,
                                     hierarchy=hierarchy,
                                     singletons=singletons)
        else:
            return "<html><body>This wiki's custom contentspage is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    security.declareProtected(Permissions.View, 'diffform')
    def diffform(self, revA, difftext, REQUEST=None):
        """
        Display a default or custom contents page. 

        May be overridden by a page template or DTML method of the same
        name.
        """
        form = getattr(self.folder(),'diffform',default_diffform)
        if isPageTemplate(form) or isDtmlMethod(form):
            return form.__of__(self)(self,REQUEST,
                                     revA=revA,
                                     difftext=difftext)
        else:
            return "<html><body>This wiki's custom diffform is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    security.declareProtected(Permissions.Edit, 'editform')
    def editform(self, REQUEST=None, page=None, text=None, action='Change'):
        """
        Display the default or a custom form to edit or create a page.

        For new pages, initial text may be specified.  May be overridden
        by a page template or DTML method of the same name.
        """
        if ((not page or page == self.pageName()) and
            hasattr(self,'wl_isLocked') and self.wl_isLocked()):
            return self.davLockDialog()

        # what are we going to do ? set up page, text & action accordingly
        if page is None:
            # no page specified - editing the current page
            page = self.title_or_id()
            text = self.read()
        #elif hasattr(self.folder(), page):
        elif self.pageWithName(page):
            # editing a different page
            text = self.pageWithName(page).read()
        else:
            # editing a brand-new page
            action = 'Create'
            text = text or ''

        # display the edit form - a dtml method or the builtin default
        # NB we redefine id as a convenience, so that one header can work
        # for pages and editforms
        # XXX can we simplify this/make dtml more version independent ?
        # NB 'id' and 'oldid' are no longer used, but provide them for
        # backwards compatibility with old templates
            
        form = getattr(self.folder(),'editform',default_editform)
        if isPageTemplate(form) or isDtmlMethod(form):
            return form.__of__(self)(self,REQUEST,
                                     page=page,
                                     text=text,
                                     action=action,
                                     id=page,
                                     oldid=self.id())
        else:
            return "<html><body>This wiki's custom editform is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    security.declareProtected(Permissions.Add, 'createform')
    def createform(self, REQUEST=None, page=None, text=None, action='Create'):
        """
        Display the default or a custom form to create a page.

        For new pages, initial text may be specified.  May be overridden
        by a page template or DTML method of the same name.

        This is editform protected by a different permission.
        """
        return self.editform(REQUEST,page,text,action)
    

#    security.declareProtected(Permissions.Edit,'xedit')
#    def xedit(self, page=None, text=None, type=None, title='', 
#              timeStamp=None, REQUEST=None, 
#              subjectSuffix='', log='', check_conflict=1,
#              leaveplaceholder=1, updatebacklinks=1,
#              subtopics=None): 
#        """
#        Convenience method to invoke external editor on this page.
#        """
#        pass

    security.declareProtected(Permissions.View, 'subscribeform')
    def subscribeform(self, REQUEST=None):
        """
        Display a default or custom mail subscription form. 

        May be overridden by a page template or DTML method of the same
        name.
        """
        form = getattr(self.folder(),'subscribeform',default_subscribeform)
        if isPageTemplate(form) or isDtmlMethod(form):
            return form.__of__(self)(self,REQUEST)
        else:
            return "<html><body>This wiki's custom subscribeform is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    security.declareProtected(Permissions.View, 'recentchanges')
    def recentchanges(self, REQUEST=None):
        """
        Return a custom or default skin-based version of RecentChanges.

        The default page template calls some DTML to do the actual work,
        for ease of syncing with the latest DTML-page-based code.
        """
        form = getattr(self.folder(),'recentchanges',default_recentchanges)
        if isPageTemplate(form) or isDtmlMethod(form):
            # XXX kludge - figure out if this template requires the dtml
            if re.search(r'"structure options/body',form.read()):
                body = default_recentchangesdtml.__of__(self)(self,REQUEST)
                return form.__of__(self)(self,REQUEST,body=body)
            else:
                return form.__of__(self)(self,REQUEST)
        else:
            return "<html><body>This wiki's custom recentchanges is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    # searchpage would be consistent with the page version, but not logical
    # search and searchform are too like existing cmf/plone objects
    # for now we'll call it searchwiki and provide a searchpage alias
    security.declareProtected(Permissions.View, 'searchwiki')
    def searchwiki(self, REQUEST=None):
        """
        Return a custom or default skin-based version of SearchPage.

        The default page template calls some DTML to do the actual work,
        for ease of syncing with the latest DTML-page-based code.
        """
        form = getattr(self.folder(),'searchwiki',default_searchwiki)
        if isPageTemplate(form) or isDtmlMethod(form):
            # XXX kludge - figure out if this template requires the dtml
            if re.search(r'"structure options/body',form.read()):
                body = default_searchwikidtml.__of__(self)(self,REQUEST)
                return form.__of__(self)(self,REQUEST,body=body)
            else:
                return form.__of__(self)(self,REQUEST)
        else:
            return "<html><body>This wiki's custom searchwiki is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    searchpage = searchwiki

    security.declareProtected(Permissions.View, 'useroptions')
    def useroptions(self, REQUEST=None):
        """
        Return a custom or default skin-based version of UserOptions.

        The default page template calls some DTML to do the actual work,
        for ease of syncing with the latest DTML-page-based code.
        """
        form = getattr(self.folder(),'useroptions',default_useroptions)
        if isPageTemplate(form) or isDtmlMethod(form):
            # XXX kludge - figure out if this template requires the dtml
            if re.search(r'"structure options/body',form.read()):
                body = default_useroptionsdtml.__of__(self)(self,REQUEST)
                return form.__of__(self)(self,REQUEST,body=body)
            else:
                return form.__of__(self)(self,REQUEST)
        else:
            return "<html><body>This wiki's custom useroptions is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    security.declareProtected(Permissions.View, 'issuetracker')
    def issuetracker(self, REQUEST=None):
        """
        Return a custom or default skin-based version of IssueTracker.

        The default page template calls some DTML to do the actual work,
        for ease of syncing with the latest DTML-page-based code.
        """
        form = getattr(self.folder(),'issuetracker',default_issuetracker)
        if isPageTemplate(form) or isDtmlMethod(form):
            # XXX kludge - figure out if this template requires the dtml
            if re.search(r'"structure options/body',form.read()):
                body = default_issuetrackerdtml.__of__(self)(self,REQUEST)
                return form.__of__(self)(self,REQUEST,body=body)
            else:
                return form.__of__(self)(self,REQUEST)
        else:
            return "<html><body>This wiki's custom issuetracker is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    security.declareProtected(Permissions.View, 'filterissues')
    def filterissues(self, REQUEST=None):
        """
        Return a custom or default skin-based version of FilterIssues.

        The default page template calls some DTML to do the actual work,
        for ease of syncing with the latest DTML-page-based code.
        """
        form = getattr(self.folder(),'filterissues',default_filterissues)
        if isPageTemplate(form) or isDtmlMethod(form):
            # XXX kludge - figure out if this template requires the dtml
            if re.search(r'"structure options/body',form.read()):
                body = default_filterissuesdtml.__of__(self)(self,REQUEST)
                return form.__of__(self)(self,REQUEST,body=body)
            else:
                return form.__of__(self)(self,REQUEST)
        else:
            return "<html><body>This wiki's custom filterissues is not a Page Template or DTML Method. Suggestion: remove it.</body></html>"

    security.declareProtected(Permissions.View, 'editConflictDialog')
    def editConflictDialog(self):
        """
        web page displayed in edit conflict situations.
        """
        titlestr=_('Edit conflict')
        return MessageDialog(
            title=titlestr,
            message="""
            <b>%s</b>
            <p>
            %s.
            %s:
            <ol>
            <li>%s
            <li>%s
            <li>%s
            <li>%s
            <li>%s.
            </ol>
            %s,
            <p>
            %s.
            """ % (
            titlestr,
            _("Someone else has saved this page while you were editing"),
            _("To resolve the conflict, do this"),
            _("Click your browser's back button"),
            _("Copy your recent edits to the clipboard"),
            _("Click your browser's refresh button"),
            _("Paste in your edits again, being mindful of the latest changes"),
            _("Click the Change button again"),
            _("or"),
            _("To discard your changes and start again, click OK"),
            ),
            action=self.page_url()+'/editform')

    security.declareProtected(Permissions.View, 'davLockDialog')
    def davLockDialog(self):
        """
        web page displayed in webDAV lock conflict situations.
        """
        titlestr=_('Page is locked')
        return MessageDialog(
            title=titlestr,
            message="""
            <b>%s</b>
            <p>
            %s
            <p>
            %s
            """ % (
            titlestr,
            _("""
            This page has a webDAV lock. Someone is probably editing it
            with an external editor.  You'll need to wait until they've
            finished and then try again.  If you've just made some changes,
            you may want to back up and copy your version of the text for
            reference.
            """),
            _("To discard your changes and try again, click OK."),
            ),
            action=self.page_url()+'/editform')

    security.declareProtected(Permissions.View, 'editConflictDialog')
    def showAccessKeys(self):
        """
        Show the access keys supported by the built-in skins.
        """
        return """
        0    show these access key assignments

        wiki functions:
        f    show front page
        c    show wiki contents
        r    show wiki recent changes
             show discussion page
             show issues page
        i    show wiki index
        o    show wiki options (preferences)
        h    show help page
        s    go to search field
        
        page functions:
        v    view page
        ,    view pages in full mode
        .    view pages in simple mode
        /    view pages in minimal mode
        m    mail subscription
        b    show backlinks (links to this page)
        d    show diffs (page edit history)
        y    show full history (in ZMI)
        e    edit this page                       
        x    edit with an external editor
             print this page (and subtopics)
        q    view page source (quick-view)
             wipe and regenerate this page's render cache
        t    go to subtopics
             go to comments (messages)
             go to page author's home page, if possible
        n    next page
        p    previous page
        u    up to parent page
        
        in edit form:
        s    save changes
        
        when viewing diffs:
        n    next edit
        p    previous edit
        """
    
Globals.InitializeClass(UI)
