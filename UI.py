# UI-related methods and utilities
#
# the GeneralForms should perhaps be moved to their respective modules

from __future__ import nested_scopes
import os, sys, re, string, time, math
import string
from string import split,join,find,lower,rfind,atoi,strip

from App.Common import rfc1123_date
from AccessControl import getSecurityManager, ClassSecurityInfo
import Permissions
from Globals import InitializeClass, MessageDialog
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS.Image import File
from Products.PageTemplates.Expressions import SecureModuleImporter

from Defaults import PAGE_METATYPE, DEFAULT_DISPLAYMODE
from Utils import BLATHER,formattedTraceback
from Regexps import htmlheaderexpr, htmlfooterexpr, htmlbodyexpr
from I18nSupport import _, DTMLFile, HTMLFile


# utilities

def loadPageTemplate(name,dir='skins/standard'):
    """
    Load the named page template from the filesystem.
    """
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
    pt = MyPTFile(os.path.join(dir,'%s.pt'%name), globals(), __name__=name)
    pt._cook_check() # ensure _text is there, we peek at it below    
    return pt

def loadDtmlMethod(name,dir='skins/standard'):
    """
    Load the named DTML method from the filesystem.
    """
    # need this one for i18n gettext patch to work ?
    #dm = DTMLFile(os.path.join(dir,name), globals())
    dm = HTMLFile(os.path.join(dir,name), globals())
    # work around some (2.7 ?) glitch
    if not hasattr(dm,'meta_type'): dm.meta_type = 'DTML Method (File)'
    return dm

def loadStylesheetFile(name,dir='skins/standard'):
    """
    Load the stylesheet File from the filesystem. Also fix a mod. time bug.
    """
    thisdir = os.path.split(os.path.abspath(__file__))[0]
    filepath = os.path.join(thisdir,dir,name)
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

def onlyBodyFrom(t):
    # XXX these can be expensive, for now just skip if there's a problem
    try:
        t = re.sub(htmlheaderexpr,'',t)
        t = re.sub(htmlfooterexpr,'',t)
    except RuntimeError: pass
    return t
    # maybe better, but more inclined to mess with valid text ?
    #return re.sub(htmlbodyexpr, r'\1', t)

def addErrorTo(text,error):
    return """<div class="error">%s</div>\n%s""" % (error,text)


DEFAULT_TEMPLATES = {
    'badtemplate'        : loadPageTemplate('badtemplate'),
    'wikipage'           : loadPageTemplate('wikipage'),
    'wikipage_macros'    : loadPageTemplate('wikipage_macros'),
    'backlinks'          : loadPageTemplate('backlinks'),
    'contentspage'       : loadPageTemplate('contentspage'),
    'diffform'           : loadPageTemplate('diffform'),
    'editform'           : loadPageTemplate('editform'),
    'subscribeform'      : loadPageTemplate('subscribeform'),
    'recentchanges'      : loadPageTemplate('recentchanges'),
    'recentchangesdtml'  : loadDtmlMethod('recentchangesdtml'),
    'searchwiki'         : loadPageTemplate('searchwiki'),
    'searchwikidtml'     : loadDtmlMethod('searchwikidtml'),
    'useroptions'        : loadPageTemplate('useroptions'),
    'useroptionsdtml'    : loadDtmlMethod('useroptionsdtml'),
    'issuetracker'       : loadPageTemplate('issuetracker'),
    'issuetrackerdtml'   : loadDtmlMethod('issuetrackerdtml'),
    'filterissues'       : loadPageTemplate('filterissues'),
    'filterissuesdtml'   : loadDtmlMethod('filterissuesdtml'),
    'stylesheet'         : loadStylesheetFile('stylesheet.css'),
    }


class UIUtils:
    """ 
    This mixin provides a generic CMF/non-CMF skin mechanism and UI utilities.

    Zwiki has a set of known "skin methods" (views) built in, which may be
    overridden by "skin templates" (page templates, dtml methods, or
    occasionally a File) of the same name. The main point of all this is 
    to provide defaults for these views when they don't exist in the ZODB.
    
    """
    security = ClassSecurityInfo()

    def defaultDisplayMode(self,REQUEST=None):
        """
        Tell the default display mode for this wiki. See displayMode.
        """
        return getattr(self.folder(),'default_displaymode',DEFAULT_DISPLAYMODE)

    def displayMode(self,REQUEST=None):
        """
        Tell the user's current display mode - full, simple, or minimal.

        This affects the standard skin's appearance; it's not used in CMF/Plone.
        This is either
        - user's zwiki_displaymode cookie, set by clicking full/simple/minimal
        - or the folder's default_displaymode string property (can acquire)
        - or DEFAULT_DISPLAYMODE
        """
        if not REQUEST: REQUEST = self.REQUEST
        return REQUEST.get('zwiki_displaymode',self.defaultDisplayMode())

    def getSkinTemplate(self,name): #,default=None):
        """
        Get the named skin template from the ZODB or filesystem.

        This will find either a Page Template or DTML Method, preferring
        the former, and return it wrapped in this page's context.  If the
        template is not found in this page's acquisition context we'll
        get it from the filesystem (ZWiki/skins/standard).
        """
        form = getattr(self.folder(),
                       name,
                       DEFAULT_TEMPLATES.get(name,
                                             DEFAULT_TEMPLATES['badtemplate']))
        if not (isPageTemplate(form) or isDtmlMethod(form)):
            form = DEFAULT_TEMPLATES['badtemplate']
        return form.__of__(self)

    security.declareProtected(Permissions.View, 'addSkinTo')
    def addSkinTo(self,body,**kw):
        """
        Apply the main view template (wikipage) to the rendered body text.

        Unless the 'bare' keyword is found in REQUEST.

        If no wikipage template is found, standard_wiki_header /
        standard_wiki_footer dtml methods will be used (legacy support).
        Specifically, use
        - the wikipage page template in our acquisition context
        - or the dtml methods, if either can be acquired
        - or the default wikipage template from the filesystem.
        """
        REQUEST = getattr(self,'REQUEST',None)
        if (#(self.supportsCMF() and self.inCMF()) or
            hasattr(REQUEST,'bare') or
            kw.has_key('bare')):
            return body

        folder = self.folder()
        skintemplate = kw.get('skin','wikipage')
        if (hasattr(folder,skintemplate) and
            isPageTemplate(getattr(folder,skintemplate))):
            return getattr(folder,skintemplate).__of__(self)(
                self,REQUEST,body=body,**kw)
        elif (hasattr(folder,'standard_wiki_header') and
              hasattr(folder,'standard_wiki_footer')):
            return self.getSkinTemplate('standard_wiki_header')(self,REQUEST)+\
                   body + \
                   self.getSkinTemplate('standard_wiki_footer')(self,REQUEST)
            #return self.standard_wiki_header(REQUEST) + \
            #       body + \
            #       self.standard_wiki_footer(REQUEST)
        else:
            return DEFAULT_TEMPLATES['wikipage'].__of__(self)(self,REQUEST,
                                                              body=body,**kw)

    # XXX
    #security.declareProtected(Permissions.View, 'standard_wiki_header')
    #def standard_wiki_header(self, REQUEST=None):
    #    """
    #    Return the custom standard_wiki_header or a warning.
    #    """
    #    if (hasattr(self.folder(),'standard_wiki_header') and
    #        isDtmlMethod(self.folder().standard_wiki_header)):
    #        return self.folder().standard_wiki_header(self,REQUEST)
    #    else:
    #        return '<html>\n<body>\nThis wiki has a custom standard_wiki_footer but no corresponding standard_wiki_header. Suggestion: remove it.\n'
    #
    #security.declareProtected(Permissions.View, 'standard_wiki_footer')
    #def standard_wiki_footer(self, REQUEST=None):
    #    """
    #    Return the custom standard_wiki_footer or a warning.
    #    """
    #    if (hasattr(self.folder(),'standard_wiki_footer') and
    #        isDtmlMethod(self.folder().standard_wiki_footer)):
    #        return self.folder().standard_wiki_footer(self,REQUEST)
    #    else:
    #        return '<p>This wiki has a custom standard_wiki_header but no corresponding standard_wiki_footer. Suggestion: remove it.</body></html>'

    security.declareProtected(Permissions.View, 'setSkinMode')
    def setSkinMode(self,REQUEST,mode):
        """
        Change the user's display mode cookie for the standard skin.
        
        The display mode affects the appearance of Zwiki's standard skin;
        it may be full, simple, or minimal.

        XXX nb keep useroptions synced with this.
        """
        RESPONSE = REQUEST.RESPONSE
        RESPONSE.setCookie('zwiki_displaymode',
                           mode,
                           path='/',
                           expires=(self.ZopeTime() + 365).rfc822()) # 1 year
        REQUEST.RESPONSE.redirect(REQUEST.get('URL1'))

    security.declareProtected(Permissions.View, 'setCMFSkin')
    def setCMFSkin(self,REQUEST,skin):
        """
        Change the user's CMF/Plone skin preference, if possible.
        """
        # are we in a CMF site ?
        if not self.inCMF(): return
        portal_skins = self.portal_url.getPortalObject().portal_skins
        portal_membership = self.portal_url.getPortalObject().portal_membership
        # does the named skin exist ?
        def hasSkin(s): return portal_skins.getSkinPath(s) != s
        if not hasSkin(skin): return
        # is the user logged in ? 
        member = portal_membership.getAuthenticatedMember()
        if not hasattr(member,'setProperties'): return
        # change their skin preference and reload page
        REQUEST.form['portal_skin'] = skin
        member.setProperties(REQUEST)
        portal_skins.updateSkinCookie()
        REQUEST.RESPONSE.redirect(REQUEST.get('URL1'))

    security.declareProtected(Permissions.View, 'setSkin')
    def setskin(self,REQUEST,skin=None):
        """
        Change the user's skin, or skin display mode.

        skin can be either a display mode of Zwiki's standard skin - full,
        simple, minimal - or the name of a CMF/Plone skin, or just plone.
        (standard skin modes can work in cmf/plone, if there is a skin
        named "Zwiki" with the "standard" layer above "zwiki_plone".)

        Calling this with no arguments will select the standard skin's
        simple mode, or the Plone Default skin if you are in CMF.
        """
        # convenient defaults:
        if not skin or skin in ['plone','cmf']:
            if self.inCMF(): skin = 'Plone Default'
            else: skin = 'simple'
        RESPONSE = REQUEST.RESPONSE
        if skin in ['full','simple','minimal']:
            self.setSkinMode(REQUEST,skin)
            self.setCMFSkin(REQUEST,'Zwiki')
        else:
            self.setCMFSkin(REQUEST,skin)

InitializeClass(UIUtils)


class GeneralForms:
    """ 
    This mixin provides most of the main UI forms/views.

    Perhaps these should move to their respective modules.
    """
    security = ClassSecurityInfo()

    security.declareProtected(Permissions.View, 'wikipage')
    def wikipage(self, dummy=None, REQUEST=None, RESPONSE=None):
        """
        Render the main page view (dummy method to allow standard skin in CMF).

        XXX this may or may not still be useful. Old comment:
        The wikipage template is usually applied by addSkinTo;
        this is provided so you can configure it as the "view" method
        in portal_types -> Wiki Page -> actions to use Zwiki's standard 
        skin inside a CMF/Plone site.
        """
        return self.render(REQUEST=REQUEST,RESPONSE=RESPONSE)

    # backwards compatibility
    wikipage_view = wikipage
           
    security.declareProtected(Permissions.View, 'wikipage_macros')
    def wikipage_macros(self, REQUEST=None):
        """
        Get the wikipage_macros page template (without evaluating).

        Template-customizable.
        """
        return self.getSkinTemplate('wikipage_macros')
           
    security.declareProtected(Permissions.View, 'stylesheet')
    def stylesheet(self, REQUEST=None):
        """
        Return the style sheet used by the other templates.

        Template-customizable. Unlike the other skin methods, this one can
        be overridden by either a 'stylesheet' or a 'stylesheet.css'
        template - this is a little annoying.

        Also the template in this case is usually a File (but can also be
        a page template or dtml method for a dynamic stylesheet). When a
        File is used the Last-modified header is set to help caching.
        (Also, all pages use a single stylesheet url -
        DEFAULTPAGE/stylesheet).
        """
        if REQUEST: REQUEST.RESPONSE.setHeader('Content-Type', 'text/css')
        #XXX self.getSkinTemplate('stylesheet')
        form = getattr(self.folder(),'stylesheet',
                       getattr(self.folder(),'stylesheet.css',
                               DEFAULT_TEMPLATES['stylesheet']
                               ))
        if isPageTemplate(form) or isDtmlMethod(form):
            return form.__of__(self)(self,REQUEST)
        else: # a File
            if REQUEST:
                modified = form.bobobase_modification_time()
                REQUEST.RESPONSE.setHeader('Last-Modified',
                                           rfc1123_date(modified))
            return form.index_html(REQUEST,REQUEST.RESPONSE)

    security.declareProtected(Permissions.View, 'backlinks')
    def backlinks(self, REQUEST=None):
        """
        Render the backlinks form (template-customizable).
        """
        return self.getSkinTemplate('backlinks')(self,REQUEST)

    security.declareProtected(Permissions.View, 'contentspage')
    def contentspage(self, hierarchy, singletons, REQUEST=None):
        """
        Render the contents view (template-customizable).

        hierarchy and singletons parameters are required.
        """
        return self.getSkinTemplate('contentspage')(self,REQUEST,
                                                    hierarchy=hierarchy,
                                                    singletons=singletons)

    security.declareProtected(Permissions.View, 'diffform')
    def diffform(self, revA, difftext, REQUEST=None):
        """
        Render the diff form (template-customizable).

        revA and difftext parameters are required.
        """
        return self.getSkinTemplate('diffform')(self,REQUEST,
                                                 revA=revA,
                                                 difftext=difftext)

    security.declareProtected(Permissions.Edit, 'editform')
    def editform(self, REQUEST=None, page=None, text=None, action='Change'):
        """
        Render the edit form (template-customizable).

        For new pages, initial text may be specified.
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
            
        return self.getSkinTemplate('editform')(self,REQUEST,
                                                page=page,
                                                text=text,
                                                action=action,
                                                id=page,
                                                oldid=self.id())

    security.declareProtected(Permissions.Add, 'createform')
    def createform(self, REQUEST=None, page=None, text=None, pagename=None):
        """
        Render the create form (template-customizable).

        This is just editform protected by a different permission.
        The new page name and initial text may be specified. 

        XXX pagename is a temporary alternate argument so the page
        management form can call this.
        """
        return self.editform(REQUEST,page or pagename,text,action='Create')
    

#    security.declareProtected(Permissions.Edit,'xedit')
#    def xedit(self): pass

    security.declareProtected(Permissions.View, 'subscribeform')
    def subscribeform(self, REQUEST=None):
        """
        Render the mail subscription form (template-customizable).
        """
        return self.getSkinTemplate('subscribeform')(self,REQUEST)

    security.declareProtected(Permissions.View, 'recentchanges')
    def recentchanges(self, REQUEST=None):
        """
        Render the recentchanges form (template-customizable).

        The default page template calls a DTML helper template,
        for ease of syncing with the evolving wiki-page-based version.
        """
        form = self.getSkinTemplate('recentchanges')
        dtmlpart = self.getSkinTemplate('recentchangesdtml')
        # XXX kludge - a customized template may not require our dtml part
        if re.search(r'"structure options/body',form.read()):
            return form(self,REQUEST,body=dtmlpart(self,REQUEST))
        else:
            return form(self,REQUEST)

    # searchpage would be consistent with the page version, but not logical
    # search and searchform are too like existing cmf/plone objects
    # for now we'll call it searchwiki and provide a searchpage alias
    security.declareProtected(Permissions.View, 'searchwiki')
    def searchwiki(self, REQUEST=None):
        """
        Render the searchwiki form (template-customizable).

        The default page template calls a DTML helper template,
        for ease of syncing with the evolving wiki-page-based version.
        """
        form = self.getSkinTemplate('searchwiki')
        dtmlpart = self.getSkinTemplate('searchwikidtml')
        # XXX kludge - a customized template may not require our dtml part
        if re.search(r'"structure options/body',form.read()):
            return form(self,REQUEST,body=dtmlpart(self,REQUEST))
        else:
            return form(self,REQUEST)

    searchpage = searchwiki

    security.declareProtected(Permissions.View, 'useroptions')
    def useroptions(self, REQUEST=None):
        """
        Render the useroptions form (template-customizable).

        The default page template calls a DTML helper template,
        for ease of syncing with the evolving wiki-page-based version.
        """
        form = self.getSkinTemplate('useroptions')
        dtmlpart = self.getSkinTemplate('useroptionsdtml')
        # XXX kludge - a customized template may not require our dtml part
        if re.search(r'"structure options/body',form.read()):
            return form(self,REQUEST,body=dtmlpart(self,REQUEST))
        else:
            return form(self,REQUEST)

    security.declareProtected(Permissions.View, 'issuetracker')
    def issuetracker(self, REQUEST=None):
        """
        Render the issuetracker form (template-customizable).

        The default page template calls a DTML helper template,
        for ease of syncing with the evolving wiki-page-based version.
        """
        form = self.getSkinTemplate('issuetracker')
        dtmlpart = self.getSkinTemplate('issuetrackerdtml')
        # XXX kludge - a customized template may not require our dtml part
        if re.search(r'"structure options/body',form.read()):
            return form(self,REQUEST,body=dtmlpart(self,REQUEST))
        else:
            return form(self,REQUEST)

    security.declareProtected(Permissions.View, 'filterissues')
    def filterissues(self, REQUEST=None):
        """
        Render the filterissues form (template-customizable).

        The default page template calls a DTML helper template,
        for ease of syncing with the evolving wiki-page-based version.
        """
        form = self.getSkinTemplate('filterissues')
        dtmlpart = self.getSkinTemplate('filterissuesdtml')
        # XXX kludge - a customized template may not require our dtml part
        if re.search(r'"structure options/body',form.read()):
            return form(self,REQUEST,body=dtmlpart(self,REQUEST))
        else:
            return form(self,REQUEST)

    security.declareProtected(Permissions.View, 'editConflictDialog')
    def editConflictDialog(self):
        """
        web page displayed in edit conflict situations.
        """
        #XXX form = self.getMessageDialog('editconflict')
        #XXX form = self.getSkinTemplate('editconflict')
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

    security.declareProtected(Permissions.View, 'showAccessKeys')
    def showAccessKeys(self):
        """
        Show the access keys supported by the built-in skins.
        """
        return _("""
        Access keys can be accessed in mozilla-based browsers by pressing alt-<key>
        IE users: must also press enter
        Mac users: command-<key>
        Opera users: shift-escape-<key>
        These won't work here, back up to the previous page to try them out.

        0    show these access key assignments

        wiki functions:
        f    show front page
        c    show wiki contents
        r    show wiki recent changes
             show discussion page
        t    show issue tracker
        i    show wiki index
        o    show wiki options (preferences)
        h    show help page
        s    go to search field
        
        page functions:
        v    view page
        +    view pages in cmf/plone skin (in a cmf/plone site)
        =    view pages in standard skin, full mode
        _    view pages in standard skin, simple mode
        -    view pages in standard skin, minimal mode
        m    mail subscription
        b    show backlinks (links to this page)
        d    show diffs (page edit history)
        y    show full history (in ZMI)
        e    edit this page                       
        x    edit with an external editor
             print this page (and subtopics)
        q    view page source (quick-view)
             wipe and regenerate this page's render cache
             go to subtopics
             go to comments (messages)
             go to page author's home page, if possible
        n    next page
        p    previous page
        u    up to parent page
        
        in edit form:
        s    save changes
        p    preview
        
        when viewing diffs:
        n    next edit
        p    previous edit
        """)
    
InitializeClass(GeneralForms)


class UI(
    UIUtils,
    GeneralForms):
    pass
