"""
Zwiki's skin mechanism and main UI view methods.

Zwiki has a built-in skin mechanism which aims to just work and be easily
customizable, whether in standard zope, CMF or Plone, without requiring
any extra products or setup. Here's the scoop:

View methods
------------
*view methods* are methods which render a particular screen in Zwiki's UI
- editform, diffform, the main page view, etc. These define the standard
wiki page views which are always available no matter what kind of site we
are in. Three examples: the main page view, the edit form, the backlinks
form, rendered by __call__(), editform(), and backlinks() respectively. We
also have helper view methods which render smaller parts of the UI. Most
view methods are defined by the SkinViews mixin below; others are defined
by plugins.

Skin templates
--------------
view methods use a *skin template* to control their rendering.  This is a
page template, dtml method or file of the same name as the method (perhaps
with a suffix added). It is found by looking first in the ZODB (current
folder, acquisition context, CMF skin layers), then on the filesystem
(plugins, ZWiki/skins/<current skin>, ZWiki/skins/zwiki) - see
getSkinTemplate for more details. The default zwiki skin provides all
the standard templates, and these may be overridden selectively.
They are listed here: http://zwiki.org/QuickReference#skin-templates

Skin macros
-----------
the standard zwiki skin uses METAL macros to break things into into
manageable pieces. These are chunks of page template which can be reused
in other page templates, in one of two ways:

1. including - the called template fills a space within the caller
2. wrapping - the called template takes over, and caller fills spaces
   (slots) within it

All of the macros in the current skin are made available to all skin
templates as here/macros.

Plone compatibility
-------------------
the standard zwiki skin templates (at least) are designed to work in both
standard zope and plone wikis. To achieve this all templates call the
"here/main_template/macros/master" macro to wrap themselves in the overall
site skin. This calls CMF/Plone's main template if we are in CMF, and
Zwiki's if we are not (or if we are in plone but have selected the zwiki skin).

Which kind of zodb object should you choose when customizing a skin template ?
------------------------------------------------------------------------------
page templates
 Zope page templates are the workhorse for making dynamic views. They
 provide better i18n features than dtml, can be well-formed HTML and can
 be edited by WYSIWYG HTML editors without harm. They can include other
 page templates or wrap themselves in other page templates using macros.

dtml methods
 Zope DTML methods are the precursor to page templates. They are a little
 faster, a little less explicit, not well-formed HTML, a little harder to
 debug, and easier to understand than page templates & macros.

files
 These are best for chunks of content which do not change much and should
 be cached. A File object works well for a stylesheet.

images
 These are like files, but better for graphics.

Other notes
-----------
- several of the standard Zwiki page templates call a dtml method to do
  their work.  This is simply a convenience so that these views may be
  installed either in the skin or as editable dtml-enabled wiki pages,
  allowing more agile development and tweaking.  Eg: recentchanges.pt and
  RecentChanges.dtml.

- the stylesheet method looks for a skin template object named
  ``stylesheet.css`` of ``stylesheet``, in that order.  See also
  http://zwiki.org/HowToSetUpAnEditableStylesheet .

- when running zope in debug mode, all filesystem-based skin templates and
  macros will refresh, showing changes immediately without a zope restart.

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
from Utils import BLATHER, formattedTraceback, abszwikipath
from I18n import _, DTMLFile, HTMLFile


def loadPageTemplate(name,dir='skins/zwiki'):
    """
    Load the named page template from the filesystem and return it, or None.
    """
    f = os.path.join(abszwikipath(dir),'%s.pt' % name)
    if os.path.exists(f):
        return PageTemplateFile(f,globals(),__name__=name)
    else:
        return None

def loadDtmlMethod(name,dir='skins/zwiki'):
    """
    Load the named dtml method from the filesystem and return it, or None.
    """
    f = os.path.join(abszwikipath(dir),name)
    if os.path.exists('%s.dtml' % f):
        # need this one for i18n gettext patch to work ?
        #dm = DTMLFile(os.path.join(dir,name), globals())
        dm = HTMLFile(f, globals())
        # work around some (2.7 ?) glitch
        if not hasattr(dm,'meta_type'): dm.meta_type = 'DTML Method (File)'
        return dm
    else:
        return None

def loadStylesheet(name,dir='skins/zwiki'):
    """
    Load the stylesheet file from the filesystem.
    """
    f = loadFile(name,dir=dir)
    if f: f.content_type = 'text/css'
    return f

def loadFile(name,dir='skins/zwiki'):
    """
    Load and return a File from the filesystem, or None.
    """
    filepath = os.path.join(abszwikipath(dir),name)
    if os.path.exists(filepath):
        f = None
        try:
            try:
                f = open(filepath,'rb')
                data = f.read()
                mtime = os.path.getmtime(filepath)
                file = File(name,'',data)
                # bug workaround: bobobase_modification_time will otherwise be current time
                file.bobobase_modification_time = lambda:mtime
                return file
            except IOError:
                return None
        finally:
            if f: f.close()
    else:
        return None

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


# load built-in zwiki skin templates from the filesystem
# skins/zwiki/ defines all of these, other skins need not

SKINS = {}
for s in os.listdir(abszwikipath('skins')):
    SKINS[s] = {}
    skindir = os.path.join(abszwikipath('skins'),s)
    for template in [
        # main view templates
        # these usually have a similarly named publish method
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
        # macro-providing templates
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
        'badtemplate',
        ]:
        obj = loadPageTemplate(template,dir=skindir)
        if obj: SKINS[s][template] = obj
    for template in [
        # helper dtml methods
        'RecentChanges',
        'SearchPage',
        'UserOptions',
        'subtopics_outline',
        'subtopics_board',
        'stylesheet',
        ]:
        obj = loadDtmlMethod(template,dir=skindir)
        if obj: SKINS[s][template] = obj
    # extras
    if s=='zwiki':
        SKINS[s]['stylesheet'] = loadStylesheet('stylesheet.css')
        # XXX this really expects to be a full wiki page
        # for now, read it as a file and format it in helppage.pt
        # one issue: File does not refresh in debug mode ?
        SKINS[s]['HelpPage'] = loadFile('HelpPage.stx',dir=skindir)

TEMPLATES = SKINS['zwiki'] # backwards compatibility

#XXX get from request
CURRENTSKIN = 'zwiki'
#CURRENTSKIN = 'nautica'

# set up easy access to all PT macros via here/macros.
MACROS = {} # a flat dictionary of all macros defined in all templates
# need to initialise it for some backwards compatibility assignments at startup
[MACROS.update(t.pt_macros()) for t in TEMPLATES.values() if isPageTemplate(t)]
def getmacros(self):
    """
    Return a dictionary of all the PT macros in the skin.

    XXX here/macros is a computed attribute calling this for each access,
    to ensure we always get the fresh macro in debug mode or when a
    template is customised in the zodb. Are we getting into performance
    concerns yet ?  Any simpler acceptable setup we can offer?
    """
    skin = SKINS[CURRENTSKIN]
    for t in skin.keys():
        if isPageTemplate(skin[t]):
            MACROS.update(self.getSkinTemplate(t).pt_macros())
    return MACROS

# provide old macros for backwards compatibility
# pre-0.52 these were defined in wikipage, old custom templates may need them
# two more were defined in contentspage, we won't support those
MACROS['linkpanel']   = MACROS['links']
MACROS['navpanel']    = MACROS['hierarchylinks']
nullmacro = ZopePageTemplate('null','<div metal:define-macro="null" />').pt_macros()['null']
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
        Return the style sheet used by the other skin templates.

        Looks for a skin template object named stylesheet.css or
        stylesheet in that order. If it is a File (the usual case), send
        appropriate headers/reponses for good caching behaviour.
        """
        REQUEST.RESPONSE.setHeader('Content-Type', 'text/css')
        form = self.getSkinTemplate('stylesheet',suffixes=['.css',''])
        if isFile(form):
            if self.handle_modified_headers(
                last_mod=form.bobobase_modification_time(), REQUEST=REQUEST):
                return ''
            else:
                return form.index_html(REQUEST,REQUEST.RESPONSE)
        else:
            return form(self,REQUEST)

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

    def getSkinTemplate(self, name, suffixes=['.pt','.dtml','']):
        """
        Get the named skin template from the ZODB or filesystem.

        A 'skin template' is responsible for some part of the Zwiki user
        interface; it may be a Page Template, DTML Method or File.  We
        look for a template with this name, first in the ZODB acquisition
        context, trying the suffixes in the order given; then in
        CURRENTSKIN on the filesystem, if CURRENTSKIN is set; and finally
        in skins/zwiki on the filesystem.  For convenient skin
        development, we return the template wrapped in the current page's
        context (so here = the page, container = the folder, etc).  If no
        matching template can be found, we return a generic error
        template.

        This somewhat duplicates the CMF skin system, but will always be
        available, and provides extra handling useful to zwiki skin
        customisers.
        """
        # look for a similarly-named template in the zodb
        for s in suffixes:
            obj = getattr(self.folder(), name+s, None)
            if obj and (isTemplate(obj) or isFile(obj)): break
            else: obj = None
        if not obj:
            # look in the selected filesystem skin, or finally in the
            # standard zwiki skin
            currentskin = CURRENTSKIN #XXX get from request
            obj = SKINS[currentskin].get(name,
                              SKINS['zwiki'].get(name,
                                            SKINS['zwiki']['badtemplate']))
        # return it, with both folder and page in the acquisition context
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
