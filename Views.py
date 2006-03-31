"""
UI-related methods and utilities.
"""

from __future__ import nested_scopes
import os, sys, re, string, time, math
import string
from string import split,join,find,lower,rfind,atoi,strip

from App.Common import rfc1123_date
from AccessControl import getSecurityManager, ClassSecurityInfo
import Permissions
from OFS.Image import File
from Globals import InitializeClass, MessageDialog
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PageTemplates.Expressions import SecureModuleImporter

from Defaults import PAGE_METATYPE, DEFAULT_DISPLAYMODE
from Utils import BLATHER,formattedTraceback
from Regexps import htmlheaderexpr, htmlfooterexpr, htmlbodyexpr
from I18n import _, DTMLFile, HTMLFile


# utilities

THISDIR = os.path.split(os.path.abspath(__file__))[0]

def loadPageTemplate(name,dir='skins/zwiki_standard'):
    """
    Load the named page template from the filesystem.
    """
    return ZopePageTemplate(
        name,
        open(os.path.join(THISDIR,dir,'%s.pt'%name),'r').read())
    #return PageTemplateFile(os.path.join(dir,'%s.pt'%name),
    #                        globals(),
    #                        __name__=name)

def loadMacros(name,dir='skins/zwiki_standard'):
    """
    Load all macros from the named page template on the filesystem.
    """
    return loadPageTemplate(name,dir).pt_macros()

def loadDtmlMethod(name,dir='skins/zwiki_standard'):
    """
    Load the named DTML method from the filesystem.
    """
    # need this one for i18n gettext patch to work ?
    #dm = DTMLFile(os.path.join(dir,name), globals())
    dm = HTMLFile(os.path.join(dir,name), globals())
    # work around some (2.7 ?) glitch
    if not hasattr(dm,'meta_type'): dm.meta_type = 'DTML Method (File)'
    return dm

def loadStylesheetFile(name,dir='skins/zwiki_standard'):
    """
    Load the stylesheet File from the filesystem. Also fix a mod. time bug.
    """
    filepath = os.path.join(THISDIR,dir,name)
    data,mtime = '',0
    try:
        fp = open(filepath,'rb')
        data = fp.read()
        mtime = os.path.getmtime(filepath)
    finally: fp.close()
    file = File('stylesheet','',data,content_type='text/css')
    # fix bobobase_mod_time which will otherwise be current time
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

def isTemplate(obj):
    return isPageTemplate(obj) or isDtmlMethod(obj)

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

# templates for the standard skin's views
STANDARD_TEMPLATES = {}
for t in [
    'badtemplate',
    'backlinks',
    'contentspage',
    'denied',
    'diffform',
    'editform',
    'maintemplate',
    'recentchanges',
    'searchwiki',
    'subscribeform',
    'useroptions',
    'wikipage',
    ]:
    STANDARD_TEMPLATES[t] = loadPageTemplate(t)

# dtml included by the default templates
for t in [
    'RecentChanges',
    'SearchPage',
    'UserOptions',
    'subtopics_outline',
    'subtopics_board',
    ]:
    STANDARD_TEMPLATES[t] = loadDtmlMethod(t)

# stylesheet
STANDARD_TEMPLATES['stylesheet'] = loadStylesheetFile('stylesheet.css')

# templates for the plone skin
# don't need to pre-load these, normal cmf skin lookup will find them
PLONE_TEMPLATES = {}

# macros in these templates will be available to all views in here.macros
MACROS = {}
for t in [
    'accesskeys',
    'commentform',
    'content',
    'head',
    'links',
    'pageheader',
    'pagemanagementform',
    'ratingform',
    'siteheader',
    ]:
    MACROS.update(loadMacros(t))
# backwards compatibility
# pre-0.52 these were defined in wikipage, old custom templates may need them
# two more were defined in contentspage, we won't support those
null = ZopePageTemplate(
    'null','<div metal:define-macro="null" />').pt_macros()['null']
for t in [
    'favicon',
    'linkpanel',
    'logolink',
    'navpanel',
    'pagelinks',
    'pagenameand',
    'wikilinks',
    ]:
    MACROS[t] = null


class SkinUtils:
    """
    This mixin provides a CMF-like skin lookup mechanism.

    This allows us to find views regardless of where we are.
    """
    security = ClassSecurityInfo()

    def hasSkinTemplate(self,name):
        """
        Does the named skin template exist in the aq context or filesystem ?
        """
        # != ignores any acquisition wrapper
        return self.getSkinTemplate(name) != STANDARD_TEMPLATES['badtemplate']
        
    def getSkinTemplate(self,name):
        """
        Get the named skin template from the ZODB or filesystem.

        This will find either a Page Template or DTML Method with the
        specified name, preferring the former, and return it wrapped
        in the current page's context.  We look first in the ZODB
        acquisition context; then in the skins/* layers on the
        filesystem, looking in zwiki_standard or zwiki_plone first
        depending on whether we're in a CMF site.  If the template
        can't be found, return a standard error template.

        This is basically duplicating the CMF skin mechanism, but in a
        way that works everywhere, and with some extra error-handling
        to help skin customizers. Still evolving, it will all shake
        out in the end.
        """
        # nb don't let a non-template shadow a template
        obj = getattr(self.folder(), name, None)
        if not isTemplate(obj):
            if not self.inCMF():
                obj = STANDARD_TEMPLATES.get(name,
                      PLONE_TEMPLATES.get(name,
                      None))
            else:
                obj = PLONE_TEMPLATES.get(name,
                      STANDARD_TEMPLATES.get(name,
                      None))
        if not isTemplate(obj):
            obj = STANDARD_TEMPLATES['badtemplate']
        return obj.__of__(self)

    # XXX
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
        #import pdb; pdb.set_trace()
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
        else:
            return STANDARD_TEMPLATES['wikipage'].__of__(self)(self,REQUEST,
                                                              body=body,**kw)

InitializeClass(SkinUtils)


class SkinSwitchingUtils:
    """
    This mixin provides methods for switching between alternate skins.
    """
    security = ClassSecurityInfo()

    def displayMode(self,REQUEST=None):
        """
        Tell the user's current display mode - full, simple, or minimal.

        This affects the standard skin's appearance; it's not used in CMF/Plone.
        This is either
        - user's zwiki_displaymode cookie, set by clicking full/simple/minimal
        - or the folder's default_displaymode string property (can acquire)
        - or DEFAULT_DISPLAYMODE

        This is kept for backwards compatibility with old zwiki skins.
        """
        if not REQUEST: REQUEST = self.REQUEST
        return REQUEST.get('zwiki_displaymode',self.defaultDisplayMode())

    def defaultDisplayMode(self,REQUEST=None):
        """
        Tell the default display mode for this wiki. See displayMode.
        """
        return getattr(self.folder(),'default_displaymode',DEFAULT_DISPLAYMODE)

    security.declareProtected(Permissions.View, 'setDisplayMode')
    def setDisplayMode(self,REQUEST,mode):
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

    setSkinMode = setDisplayMode #backwards compatibility

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
        # is the user logged in ? if not, return harmlessly
        member = portal_membership.getAuthenticatedMember()
        if not hasattr(member,'setProperties'): return
        # change their skin preference and reload page
        REQUEST.form['portal_skin'] = skin
        member.setProperties(REQUEST)
        portal_skins.updateSkinCookie()
        REQUEST.RESPONSE.redirect(REQUEST.get('URL1'))

    security.declareProtected(Permissions.View, 'setskin')
    def setskin(self,REQUEST,skin=None):
        """
        Change the user's cmf/plone skin or standard skin display mode.

        This can be used to select a different CMF/Plone skin - primarily
        used for switching to the standard zwiki skin inside a plone site.
        To enable this you need to copy the default skin in portal_skins,
        name it "Zwiki", and add the "zwiki_standard" layer above
        "zwiki_plone". Cf http://zwiki.org/HowToUseTheStandardSkinInPlone .

        It can also change the full/simple/minimal display mode of the
        standard skin. This feature has been retired from the standard
        skin, it remains here for backwards compatibility with old
        wikis.

        skin can be any of: full, simple, minimal, Zwiki, standard, the
        name of a CMF/Plone skin, plone, cmf, or None (the last three are
        an alias for "Plone Default", standard is an alias for "Zwiki").

        I might have impaired this a bit in the post-0.43 cleanup.
        """
        RESPONSE = REQUEST.RESPONSE
        if skin in ['full','simple','minimal']:
            self.setSkinMode(REQUEST,skin)
            skin = 'Zwiki'
        if not self.inCMF(): return
        if skin == 'standard':
            skin = 'Zwiki'
        if not skin or skin in ['plone','cmf']:
            skin = 'Plone Default'
        self.setCMFSkin(REQUEST,skin)

InitializeClass(SkinSwitchingUtils)


class SkinViews:
    """ 
    This mixin provides methods for accessing the main UI views.

    These methods may be overridden by ZODB skin templates (page
    templates, dtml methods, sometimes a File) of the same name,
    otherwise will use the defaults on the filesystem.
    """
    security = ClassSecurityInfo()

    macros = MACROS

    security.declareProtected(Permissions.View, 'wikipage')
    def wikipage(self, dummy=None, REQUEST=None, RESPONSE=None):
        """
        Render the main page view (dummy method to allow standard skin in CMF).

        XXX should be going away soon. Old comment: the wikipage template
        is usually applied by __call__ -> addSkinTo, but this method is
        provided so you can configure it as the"view" action
        in portal_types -> Wiki Page -> actions and get use Zwiki's standard 
        skin inside a CMF/Plone site.
        """
        return self.render(REQUEST=REQUEST,RESPONSE=RESPONSE)

    # backwards compatibility
    wikipage_view = wikipage
    # old templates look for wikipage_template().macros
    def wikipage_template(self, REQUEST=None): return self
    wikipage_macros = wikipage_template


    security.declareProtected(Permissions.View, 'maintemplate')
    def maintemplate(self, REQUEST=None):
        """
        Return the standard or plone main_template, unevaluated.

        This provides a plone-like main_template which all other
        templates can use, whether we are in plone or not.
        """
        # XXX not really working out yet.. need this hack
        # all skin templates wrap themselves with main_template
        # in CMF, use the cmf/plone one, otherwise use ours
        # should allow use of ours in cmf/plone also
        if self.inCMF():
            return self.getSkinTemplate('main_template')
        else:
            return self.getSkinTemplate('maintemplate')
    # and make here/main_template/macros/... work
    from ComputedAttribute import ComputedAttribute
    main_template = ComputedAttribute(maintemplate,1)

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
                               STANDARD_TEMPLATES['stylesheet']
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

        This is usually called by createform also, and can handle both
        editing and creating. The form's textarea contents may be specified.
        """
        if not self.checkSufficientId(REQUEST):
            return self.denied(
                _("Sorry, this wiki doesn't allow anonymous edits. Please configure a username in options first."))
        
        if ((not page or page == self.pageName()) and
            hasattr(self,'wl_isLocked') and self.wl_isLocked()):
            return self.davLockDialog()

        # what are we going to do ? set up page, text & action accordingly
        if page is None:
            # no page specified - editing the current page
            page = self.pageName()
            text = self.read()
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

        This usually just calls editform; it is protected by a
        different permission and also allows an alternate pagename
        argument to support the page management form (XXX temporary).
        It may also be customized by a createform skin template, in
        which case page creation and page editing forms are different.
        """
        if not self.checkSufficientId(REQUEST):
            return self.denied(
                _("Sorry, this wiki doesn't allow anonymous edits. Please configure a username in options first."))

        if self.hasSkinTemplate('createform'):
            return self.getSkinTemplate('createform')(
                REQUEST, page or pagename, text)
        else:
            return self.editform(
                REQUEST, page or pagename, text, action='Create')

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
        """
        return self.getSkinTemplate('recentchanges')(self,REQUEST)

    # we call this searchwiki, not searchpage, for clarity
    security.declareProtected(Permissions.View, 'searchwiki')
    def searchwiki(self, REQUEST=None):
        """
        Render the searchwiki form (template-customizable).
        """
        return self.getSkinTemplate('searchwiki')(self,REQUEST)

    searchpage = searchwiki # alias

    security.declareProtected(Permissions.View, 'useroptions')
    def useroptions(self, REQUEST=None):
        """
        Render the useroptions form (template-customizable).
        """
        return self.getSkinTemplate('useroptions')(self,REQUEST)

    security.declarePublic('denied')
    def denied(self, reason=None, REQUEST=None):
        """
        Render the denied form (template-customizable).
        """
        return self.getSkinTemplate('denied')(self,REQUEST,reason=reason)

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
        +    (in a plone/cmf site with skin switching set up) use zwiki's plone/cmf skin
        -    (in a plone/cmf site with skin switching set up) use zwiki's standard skin
        v    view page
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
    
InitializeClass(SkinViews)


class PageViews(
    SkinUtils,
    SkinSwitchingUtils,
    SkinViews,
    ):
    pass
