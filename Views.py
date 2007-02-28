"""
Zwiki's main UI views and UI-related utilities.

Zwiki needs to work both outside and inside Plone/CMF, so cannot rely on
the CMF skin mechanism alone. There is a built-in mechanism which works
like this:

Overview
--------

- *view methods* are defined for wiki pages (via mixin class, usually in
  Views.py). These define the standard views which are always available no
  matter what kind of site we are in (main view, editform, backlinks etc.)

- view methods usually call a *view template* of the same name to render
  the view, sometimes passing data as arguments. These templates can be
  customized by wiki admins.

- view methods use getSkinTemplate() to find their helper templates. It
  looks for a page template or dtml method of the specified name, in the
  following places:

  1. first, in the wiki folder in the ZODB

  2. or, elsewhere in the ZODB by acquisition (including the CMF skin
     layers if we are in a CMF/Plone site)

  3. finally, in a built-in TEMPLATES dictionary containing the skin
     templates defined by the files in skins/zwiki/ (and others registered
     by plugins).

More about templates
--------------------

- the standard templates use METAL macros so that they can be broken up
  into manageable chunks (like the comment form) and reused easily.
  Usually there is a template file to define each macro, but this is just
  convention. At runtime all the macros are gathered from TEMPLATES and
  made available as here/macros.

- Currently all templates, except those provided by plugins, are defined
  in skins/zwiki and are designed to work in both standard and CMF/Plone
  wikis.  The need to be compatible with CMF/Plone's main_template puts
  certain constraints on Zwiki's templates.

- view templates call the here/main_template/macros/master macro to wrap
  themselves in the overall site skin. This calls CMF/Plone's main
  template if we are in CMF, or Zwiki's if we are not. (main_template is a
  ComputedAttribute on zwiki pages, which calls the get_main_template method,
  which calls CMF/Plone's main_template or Zwiki's main_template_zwiki template).

Skin object types
-----------------

Aside from the view methods, which are built in to the product code, all
skin objects - view templates, helper templates, dtml methods, files,
images - may be customized in the ZODB. Here's a review:

**page templates**
  Zope page templates are the workhorse for making dynamic views. They
  provide better i18n features than dtml. Zwiki's are well-formed HTML and
  can be edited in a wysiwyg html editor without damage (untried).

**macros**
  METAL macros are chunks of page template which can be reused in other
  page templates. They are more powerful than a simple include mechanism,
  you could say they are used in one of two ways:

  1. filling - called template fills a space within the caller
  2. wrapping - called template takes over, and caller fills spaces
     (slots) within it

**dtml methods**
  Zope DTML methods are the precursor to page templates. They are a little
  faster, a little less explicit, not well-formed HTML, a little harder to
  debug, easier to understand than macros.

**files**
  Best for chunks of content which do not change much and should be
  cached. A File object works well when customizing the stylesheet (though
  see below).

**images**
  Like files, but better suited to graphics. The zwiki skin includes a
  couple of icons.

Other notes
-----------
  
- several Zwiki views (eg recentchanges) are developed iteratively as dtml
  wiki pages on zwiki.org.  These are reused in the skin as dtml methods
  (RecentChanges.dtml) embedded within page templates
  (recentchanges.pt). The page templates may be customized to not use dtml
  if preferred.

- the stylesheet view method will accept a skin object called
  ``stylesheet`` *or* ``stylesheet.css``.  It may be a File object, a DTML
  Method, or an editable wiki page (see
  http://zwiki.org/HowToSetUpAnEditableStylesheet).

- from 0.54, all of the built in filesystem-based templates, dtml methods
  and macros refresh when running in debug mode.

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
from ComputedAttribute import ComputedAttribute

from Defaults import PAGE_METATYPE
from Utils import BLATHER, formattedTraceback
from I18n import _, DTMLFile, HTMLFile


# utilities

def loadPageTemplate(name,dir='skins/zwiki'):
    """
    Load the named page template from the filesystem.
    """
    return PageTemplateFile(
        os.path.join(dir,'%s.pt' % name),
        globals(),
        __name__=name)

def loadDtmlMethod(name,dir='skins/zwiki'):
    """
    Load the named DTML method from the filesystem.
    """
    # need this one for i18n gettext patch to work ?
    #dm = DTMLFile(os.path.join(dir,name), globals())
    dm = HTMLFile(os.path.join(dir,name), globals())
    # work around some (2.7 ?) glitch
    if not hasattr(dm,'meta_type'): dm.meta_type = 'DTML Method (File)'
    return dm

def loadStylesheet(name,dir='skins/zwiki'):
    """
    Load the stylesheet file from the filesystem.
    """
    f = loadFile(name,dir=dir)
    if f:
        f.content_type = 'text/css'
        return f

def loadFile(name,dir='skins/zwiki'):
    """
    Load a File from the filesystem.

    Also work around a modification time bug.
    """
    THISDIR = os.path.split(os.path.abspath(__file__))[0]
    filepath = os.path.join(THISDIR,dir,name)
    data,mtime = '',0
    try:
        try:
            fp = open(filepath,'rb')
            data = fp.read()
            mtime = os.path.getmtime(filepath)
            file = File('stylesheet','',data)
            # bug workaround: bobobase_modification_time will otherwise be current time
            file.bobobase_modification_time = lambda:mtime
            return file # whee! does the finally first
        except:
            return None
    finally:
        fp.close()


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

def addErrorTo(text,error):
    return """<div class="error">%s</div>\n%s""" % (error,text)


# the standard zwiki skin templates
TEMPLATES = {}
for t in [
    # main view templates
    'badtemplate', # should be first
    'backlinks',
    'contentspage',
    'denied',
    'diffform',
    'editform',
    'recentchanges',
    'searchwiki',
    'helppage',
    'subscribeform',
    'useroptions',
    'wikipage',
    # additional macro-providing templates
    'accesskeys',
    'commentform',
    'content',
    'head',
    'hierarchylinks',
    'links',
    'maintemplate',
    'pageheader',
    'pagemanagementform',
    'siteheader',
    'testtemplate',
    ]:
    TEMPLATES[t] = loadPageTemplate(t)

# helper dtml methods
for t in [
    'RecentChanges',
    'SearchPage',
    'UserOptions',
    'subtopics_outline',
    'subtopics_board',
    ]:
    TEMPLATES[t] = loadDtmlMethod(t)

# other things
TEMPLATES['stylesheet'] = loadStylesheet('stylesheet.css')
# XXX this really expects to be a full wiki page
# for now, read it as a file and format it in helppage.pt
# one issue: File does not refresh in debug mode ?
TEMPLATES['HelpPage'] = loadFile('HelpPage.stx')


# set up easy access to all macros via here/macros.
# XXX We use a computed attribute (below) to call getmacros on each
# access, to ensure they are always fresh in debug mode - or when a zodb
# template is customized. Right ?  So we have to check for customized
# templates each time. getmacros is called a lot, are we getting into
# performance concerns yet ? This seems a lot of work, there must
# be some simpler acceptable setup we can offer.
# we'll save the list of initial ZPT ids and check only these
PAGETEMPLATEIDS = [t for t in TEMPLATES.keys()
                   if isinstance(TEMPLATES[t],PageTemplateFile)]
#XXX temp - need at least this too, it defines a macro
PAGETEMPLATEIDS.extend(['ratingform'])
MACROS = {}
def getmacros(self):
    """
    Return a dictionary of all the latest macros from our PageTemplateFiles.

    This is called for each access to here/macros (MACROS)
    """
    if not self:
        # for initialisation, just use standard templates
        [MACROS.update(t.pt_macros())
         for t in TEMPLATES.values() if isinstance(t,PageTemplateFile)]
    else:
        # when called in zope context, reflect any zodb customizations
        for id in PAGETEMPLATEIDS:
            MACROS.update(self.getSkinTemplate(id).pt_macros())
    return MACROS

# provide old macros for backwards compatibility
# pre-0.52 these were defined in wikipage, old custom templates may need them
# two more were defined in contentspage, we won't support those
getmacros(None)
MACROS['linkpanel']   = MACROS['links']
MACROS['navpanel']    = MACROS['hierarchylinks']
nullmacro = ZopePageTemplate(
    'null','<div metal:define-macro="null" />').pt_macros()['null']
MACROS['favicon']     = nullmacro
MACROS['logolink']    = nullmacro
MACROS['pagelinks']   = nullmacro
MACROS['pagenameand'] = nullmacro
MACROS['wikilinks']   = nullmacro



class SkinViews:
    """ 
    This mixin defines the main Zwiki UI views as methods.

    These view methods usually just call a built-in template of the same
    name, which may be overridden by a similarly-named template in the
    ZODB (a page template, a dtml method, sometimes a File..) A few
    methods don't use a template at all.
    """
    security = ClassSecurityInfo()

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
            action=self.pageUrl()+'/editform')

    security.declarePublic('denied')
    def denied(self, reason=None, REQUEST=None):
        """
        Render the denied form (template-customizable).
        """
        return self.getSkinTemplate('denied')(self,REQUEST,reason=reason)

    security.declareProtected(Permissions.View, 'diffform')
    def diffform(self, revA, difftext, REQUEST=None):
        """
        Render the diff form (template-customizable).

        revA and difftext parameters are required.
        """
        return self.getSkinTemplate('diffform')(self,REQUEST,
                                                 revA=revA,
                                                 difftext=difftext)

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
            action=self.pageUrl()+'/editform')

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

    security.declareProtected(Permissions.View, 'helppage')
    def helppage(self, REQUEST=None):
        """
        Render the helppage form (template-customizable).
        """
        return self.getSkinTemplate('helppage')(self,REQUEST)

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
                               TEMPLATES['stylesheet']
                               ))
        if isPageTemplate(form) or isDtmlMethod(form):
            return form.__of__(self)(self,REQUEST)
        else: # a File
            if REQUEST:
                modified = form.bobobase_modification_time()
                if self.handle_modified_headers(last_mod=modified, REQUEST=REQUEST):
                    return ''
            return form.index_html(REQUEST,REQUEST.RESPONSE)

    security.declareProtected(Permissions.View, 'subscribeform')
    def subscribeform(self, REQUEST=None):
        """
        Render the mail subscription form (template-customizable).
        """
        return self.getSkinTemplate('subscribeform')(self,REQUEST)

    security.declareProtected(Permissions.View, 'useroptions')
    def useroptions(self, REQUEST=None):
        """
        Render the useroptions form (template-customizable).
        """
        return self.getSkinTemplate('useroptions')(self,REQUEST)

InitializeClass(SkinViews)



class SkinUtils:
    """
    This mixin provides utilities for our views, so that they can work in
    any kind of configuration - default or customized, standard or
    cmf/plone, old or new templates..
    """
    security = ClassSecurityInfo()

    # make MACROS available to all templates as here/macros
    macros = ComputedAttribute(getmacros,1)

    ## backwards compatibility - some old plone wikis expect wikipage_view
    ## or wikipage actions ?
    #security.declareProtected(Permissions.View, 'wikipage')
    #def wikipage(self, dummy=None, REQUEST=None, RESPONSE=None):
    #    """
    #    Render the main page view (dummy method to allow standard skin in CMF).
    #
    #    XXX should be going away soon. Old comment: the wikipage template
    #    is usually applied by __call__ -> addSkinTo, but this method is
    #    provided so you can configure it as the"view" action
    #    in portal_types -> Wiki Page -> actions and get use Zwiki's standard 
    #    skin inside a CMF/Plone site.
    #    """
    #    return self.render(REQUEST=REQUEST,RESPONSE=RESPONSE)
    #wikipage_view = wikipage
    
    # backwards compatibility - some old templates expect
    # wikipage_template().macros or wikipage_macros something something
    def wikipage_template(self, REQUEST=None): return self
    wikipage_macros = wikipage_template

    security.declareProtected(Permissions.View, 'getmaintemplate')
    def getmaintemplate(self, REQUEST=None):
        """
        Return the standard Zwiki or CMF/Plone main template, unevaluated.

        This fetches the appropriate main template depending on whether we
        are in or out of cmf/plone (and in the latter case, whether the
        user has selected standard or plone skin mode). We point the
        'main_template' computed attribute at this method, which allows
        our templates to use here/main_template and always be
        appropriately skinned.
        """
        # XXX not really working out yet.. need this hack
        # all skin templates wrap themselves with main_template
        # in CMF, use the cmf/plone one, otherwise use ours
        # should allow use of ours in cmf/plone also
        if self.inCMF() and self.displayMode() == 'plone':
            return self.getSkinTemplate('main_template') # plone's
        else:
            return self.getSkinTemplate('maintemplate')  # zwiki's
    main_template = ComputedAttribute(getmaintemplate,1)

    def getSkinTemplate(self,name):
        """
        Get the named skin template from the ZODB or filesystem.

        This will find either a Page Template or DTML Method with the
        specified name. We look first for a template with this name in the
        ZODB acquisition context, trying the .pt, .dtml or no suffix in
        that order. Then we look in skins/zwiki on the filesystem. If no
        matching template can be found, we return a generic error template.

        For convenient skin development, we return the template wrapped in
        the current page's context (so here will be the page, container
        will be the folder, etc).
                
        This is basically duplicating the CMF skin mechanism, but in a
        way that works everywhere, and with some extra error-handling
        to help skin customizers. Still evolving, it will all shake
        out in the end.
        """
        obj = getattr(self.folder(), name+'.pt',
                      getattr(self.folder(), name+'.dtml',
                              getattr(self.folder(), name,
                                      None)))
        if not isTemplate(obj): # don't accept a non-template object
            obj = TEMPLATES.get(name, TEMPLATES['badtemplate'])
        # return it with both folder and page in the acquisition context,
        # setting container and here
        return obj.__of__(self.folder()).__of__(self)

    def hasSkinTemplate(self,name):
        """
        Does the named skin template exist in the aq context or filesystem ?
        """
        # != ignores any acquisition wrapper
        return self.getSkinTemplate(name) != TEMPLATES['badtemplate']
        
    security.declareProtected(Permissions.View, 'addSkinTo')
    def addSkinTo(self,body,**kw):
        """
        Add the main wiki page skin to some body text, unless 'bare' is set.

        XXX used only for the main page view. Perhaps a wikipage view
        method should replace it ? Well for now this is called by the page
        type render methods, which lets them say whether the skin is
        applied or not.
        """
        REQUEST = getattr(self,'REQUEST',None)
        if (hasattr(REQUEST,'bare') or kw.has_key('bare')):
            return body
        else:
            return self.getSkinTemplate('wikipage')(self,REQUEST,body=body,**kw)

InitializeClass(SkinUtils)



class SkinSwitchingUtils:
    """
    This mixin provides methods for switching between alternate skins
    (or between display modes within a single zope skin).
    """
    security = ClassSecurityInfo()

    security.declareProtected(Permissions.View, 'setskin')
    def setskin(self,skin=None):
        """
        When in a CMF/Plone site, switch between standard and plonish UI.

        The user's preferred skin mode is stored in a zwiki_displaymode
        cookie.  This was once used to change the appearance of the
        non-plone standard skin (full/simple/minimal); later it acquired
        the ability to switch between CMF skins in CMF/plone; now it just
        selects the zwiki or plone appearance in CMF/plone, by setting a
        cookie for getmaintemplate().
        """
        if skin in ('plone', 'cmf'):
            self.setDisplayMode('plone')
        else:
            self.setDisplayMode('zwiki')

    security.declareProtected(Permissions.View, 'setDisplayMode')
    def setDisplayMode(self,mode):
        """
        Save the user's choice of skin mode as a cookie.

        For 1 year, should they be permanent ?
        """
        REQUEST = self.REQUEST
        RESPONSE = REQUEST.RESPONSE
        RESPONSE.setCookie('zwiki_displaymode',
                           mode,
                           path='/',
                           expires=(self.ZopeTime() + 365).rfc822())
        RESPONSE.redirect(REQUEST.get('came_from',
                                      REQUEST.get('URL1')))

    setSkinMode = setDisplayMode #backwards compatibility

    security.declareProtected(Permissions.View, 'displayMode')
    def displayMode(self,REQUEST=None):
        """
        Find out the user's preferred skin mode.
        """
        REQUEST = REQUEST or self.REQUEST
        defaultmode = (self.inCMF() and 'plone') or 'zwiki'
        m = REQUEST.get('zwiki_displaymode', None)
        if not m in ['zwiki','plone']:
            m = defaultmode
        return m

    security.declareProtected(Permissions.View, 'usingPloneSkin')
    def usingPloneSkin(self,REQUEST=None):
        """
        Convenience utility for templates: are we using plone skin ?

        Ie, are we using the plone display mode of zwiki's standard skin.
        """
        return (self.inCMF() and self.displayMode()=='plone')
        
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

InitializeClass(SkinSwitchingUtils)


class PageViews(
    SkinViews,
    SkinUtils,
    SkinSwitchingUtils,
    ):
    pass
