# product initialization

__doc__="""
ZWiki product
"""
__version__='2.0b1'

import re, os.path, string, urllib

from AccessControl import getSecurityManager
from DateTime import DateTime
from App.Common import package_home
from App.Dialogs import MessageDialog
from App.ImageFile import ImageFile
from OFS.Folder import Folder
from OFS.Image import Image, File
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PythonScripts.PythonScript import PythonScript

import Defaults, OutlineSupport, Permissions, ZWikiPage
from Admin import addDTMLMethod
from i18n import _, DTMLFile
from plugins.pagetypes import PAGETYPES
from Utils import parseHeadersBody, safe_hasattr, INFO, BLATHER, \
     formattedTraceback
from Splitter import UnicodeWordSplitter, UnicodeHTMLWordSplitter, UnicodeCaseNormalizer


# make sure old page type objects don't break
# __module_aliases__ = (
#     ('Products.ZWiki.plugins.latexwiki.stxlatex', Products.ZWiki.plugins.pagetypes),
#     ('Products.ZWiki.pagetypes', Products.ZWiki.plugins.pagetypes), # ZwikiHtmlPageType, ZwikiMoinPageType, ZwikiPlaintextPageType, ZwikiRstPageType, ZwikiStxPageType, ZwikiWwmlPageType
#     #('Products.ZWiki.pagetypes.common', Products.ZWiki.plugins.pagetypes.common),
#     ('Products.ZWiki.pagetypes.rst', Products.ZWiki.plugins.pagetypes),
#     ('Products.ZWiki.pagetypes.stx', Products.ZWiki.plugins.pagetypes),
#     ('Products.ZWiki.pagetypes.html', Products.ZWiki.plugins.pagetypes),
#     ('Products.ZWiki.pagetypes.plaintext', Products.ZWiki.plugins.pagetypes),
#     ('Products.ZWiki.pagetypes.wwml', Products.ZWiki.plugins.pagetypes),
#     ('Products.ZWiki.pagetypes.moin', Products.ZWiki.plugins.pagetypes),
#     )

misc_ = {
    'ZWikiPage_icon': ImageFile(os.path.join('skins','zwiki','wikipage_icon.gif'), globals()),
    # backwards compatibility
    'ZWikiPage_icon.gif': ImageFile(os.path.join('skins','zwiki','wikipage_icon.gif'),globals()),
    # for the rating plugin
    'star_icon': ImageFile(os.path.join('skins','zwiki','star.png'),globals()),
    'blank_star_icon': ImageFile(os.path.join('skins','zwiki','blank_star.png'),globals()),
    }

def initialize(context):
    """Initialize the ZWiki product.
    """
    try:
        # register the wiki page class
        context.registerClass(
            ZWikiPage.ZWikiPage,
            #I want to change the zmi add menu.. but not the meta_type
            #meta_type=Defaults.PAGE_ADD_MENU_NAME,
            permission=Permissions.Add,
            icon = 'skins/zwiki/wikipage_icon.gif',
            constructors = (
                ZWikiPage.manage_addZWikiPageForm,
                ZWikiPage.manage_addZWikiPage,
                ),
            )
        # also the PersistentOutline class, so it's zmi-manageable
        def outlineConstructorStub(self):
            return MessageDialog(
                title=_("No need to add a Zwiki Outline Cache"),
                message=_("""Zwiki Outline Cache appears in the ZMI Add menu
                for implementation reasons, but should not be added directly.
                Zwiki will create it for you as needed."""))
        context.registerClass(
            OutlineSupport.PersistentOutline,
            permission=Permissions.manage_properties,
            #icon = 'images/ZWikiPage_icon.gif',
            constructors = (outlineConstructorStub,)
            )
        # set up an "add wiki" menu item
        context.registerClass(
            Folder,
            meta_type=Defaults.WIKI_ADD_MENU_NAME,
            permission=Permissions.AddWiki,
            #icon = 'images/Wiki_icon.gif'
            constructors = (
                manage_addWikiForm,
                manage_addWiki,
                listWikis,
                listZodbWikis,
                listFsWikis,
                addWikiFromFs,
                addWikiFromZodb,
                )
            )
        initializeForCMF(context)
        initializeForFSS(context)

    # don't let any error prevent initialization
    except:
        INFO('failed to initialise',formattedTraceback())

# default_perms = {
#     'create': 'nonanon',
#     'edit': 'nonanon',
#     'comment': 'nonanon',
#     'move': 'owners', # rename/delete/reparent
#     'regulate': 'owners'
#     }

def initializeForCMF(context):
    """Do global CMF/Plone-specific initialization, if they are installed."""
    try:
        import Products.CMFCore.DirectoryView
        from Products.CMFCore.utils import ContentInit
        #from Products.CMFCore.permissions import AddPortalContent
        #from Products.Archetypes.public import listTypes, process_types
        from Products.CMFPlone.interfaces import IPloneSiteRoot
        from Products.GenericSetup import EXTENSION, profile_registry
    except ImportError:
        return
    BLATHER('registering "zwiki" skin layer and "Wiki Page" content type with Plone')
    # register our GenericSetup profiles
    profile_registry.registerProfile('default',
                                     'ZWiki',
                                     'Extension profile for default Zwiki-in-Plone/CMF setup',
                                     'profiles/default',
                                     'ZWiki',
                                     EXTENSION,
                                     for_=IPloneSiteRoot)
    profile_registry.registerProfile('uninstall',
                                     'ZWiki',
                                     'Extension profile for removing default Zwiki-in-Plone/CMF setup',
                                     'profiles/uninstall',
                                     'ZWiki',
                                     EXTENSION)
    # register our skin layer(s)
    Products.CMFCore.DirectoryView.registerDirectory('skins', globals())
    # initialize portal content
    PROJECT = 'Zwiki'
    #types, cons, ftis = process_types(listTypes(PROJECT),PROJECT)
    ContentInit(
        PROJECT + ' Content',
        content_types      = (ZWikiPage.ZWikiPage,), # types,
        #permission         = AddPortalContent,   # Add portal content
        permission         = Permissions.Add,     # Zwiki: Add pages
        extra_constructors = (addWikiPageInCMF,), # cons
        #fti                = ftis,               # ignored
        ).initialize(context)

# a (old-style) CMF factory method
def addWikiPageInCMF(self, id, title='', page_type=None, file=''):
    def makeWikiPage(id, title, file):
        def initPageMetadata(page):
            page.creation_date = DateTime()
            page._editMetadata(title='',
                               subject=(),
                               description='',
                               contributors=(),
                               effective_date=None,
                               expiration_date=None,
                               format='text_html',
                               language='',
                               rights = '')

        ob = ZWikiPage.ZWikiPage(source_string=file, __name__=id)
        ob.title = title
        ob.parents = []
        username = getSecurityManager().getUser().getUserName()
        ob.manage_addLocalRoles(username, ['Owner'])
        initPageMetadata(ob)
        return ob

    id=str(id)
    title=str(title)
    ob = makeWikiPage(id, title, file)
    ob.setPageType(
        page_type or getattr(self,'allowed_page_types',[None])[0])
    self._setObject(id, ob)

def initializeForFSS(context):
    """Do FileSystemSite-specific initialization, if it is installed."""
    try:
        from Products.FileSystemSite.DirectoryView import registerDirectory
        # register our skin layer as a customizable directory
        registerDirectory('skins/zwiki', globals())
        INFO('registered zwiki skin layer with FileSystemSite')
    except ImportError:
        pass


# set up hooks for ZMI operations on zwiki objects, for:
#
# 1. setting zwiki creator information
# We do this for a newly-added page object, but not one
# that has just been renamed or imported.
#
# 2. updating the wiki outline cache
# Note: manage_renameObject will lose parentage in the wiki outline (?)
#
# 3. catalog awareness
#
# XXX convert to events

def manage_afterAdd(self, item, container):
    if not self.hasCreatorInfo():
        self.setCreator(getattr(self,'REQUEST',None))
    self.wikiOutline().add(self.pageName())
    self.index_object()
ZWikiPage.ZWikiPage.manage_afterAdd = manage_afterAdd

def manage_afterClone(self, item):
    if not self.hasCreatorInfo():
        self.setCreator(getattr(self,'REQUEST',None))
    self.wikiOutline().add(self.pageName())
    self.index_object()
ZWikiPage.ZWikiPage.manage_afterClone = manage_afterClone

def manage_beforeDelete(self, item, container):
    # update the wiki outline, but if it's out of date just ignore
    try: self.wikiOutline().delete(self.pageName())
    except KeyError: pass
    self.unindex_object()
ZWikiPage.ZWikiPage.manage_beforeDelete = manage_beforeDelete

original_addProperty = ZWikiPage.ZWikiPage.manage_addProperty
def manage_addProperty(self, id, value, type, REQUEST=None):
    """Add property and reindex"""
    r = original_addProperty(self,id,value,type,REQUEST)
    self.reindex_object()
    return r
ZWikiPage.ZWikiPage.manage_addProperty = manage_addProperty

original_delProperties = ZWikiPage.ZWikiPage.manage_delProperties
def manage_delProperties(self, ids=None, REQUEST=None):
    """Delete properties and reindex"""
    r = original_delProperties(self, ids, REQUEST)
    self.reindex_object()
    return r
ZWikiPage.ZWikiPage.manage_delProperties = manage_delProperties

original_changeProperties = ZWikiPage.ZWikiPage.manage_changeProperties
def manage_changeProperties(self, REQUEST=None, **kw):
    """Update properties and reindex"""
    r = apply(original_changeProperties,(self, REQUEST), kw)
    self.reindex_object()
    return r
ZWikiPage.ZWikiPage.manage_changeProperties = manage_changeProperties

original_editProperties = ZWikiPage.ZWikiPage.manage_editProperties
def manage_editProperties(self, REQUEST):
    """Edit Properties and reindex"""
    r = original_editProperties(self, REQUEST)
    self.reindex_object()
    return r
ZWikiPage.ZWikiPage.manage_editProperties = manage_editProperties

######################################################################
# and here are functions for adding new wikis

manage_addWikiForm = DTMLFile('skins/zwiki/addwikiform', globals())

def manage_addWiki(self, new_id, new_title='', wiki_type='basic',
                       REQUEST=None, enter=0):
    """
    Create a new zwiki web of the specified type
    """
    # check for a configuration wizard
    if safe_hasattr(self,wiki_type+'_config'):
        if REQUEST:
            REQUEST.RESPONSE.redirect('%s/%s_config?new_id=%s&new_title=%s' % \
                                      (REQUEST['URL1'],
                                       wiki_type,
                                       urllib.quote(new_id),
                                       urllib.quote(new_title)))

    else:
        if wiki_type in self.listFsWikis():
            self.addWikiFromFs(new_id,new_title,wiki_type,REQUEST)
        elif wiki_type in self.listZodbWikis():
            self.addWikiFromZodb(new_id,new_title,wiki_type,REQUEST)
        else:
            if REQUEST:
                return MessageDialog(
                    title=_('Unknown wiki type'),
                    message='',
                    action=''
                    )
            else:
                raise AttributeError, (
                    _('The requested wiki type does not exist.'))

        if REQUEST:
            folder = getattr(self, new_id)
            if safe_hasattr(folder, 'setup_%s'%(wiki_type)):
                REQUEST.RESPONSE.redirect(REQUEST['URL3']+'/'+new_id+'/setup_%s'%(wiki_type))
            elif enter:
                # can't see why this doesn't work after addWikiFromFs
                #REQUEST.RESPONSE.redirect(getattr(self,new_id).absolute_url())
                REQUEST.RESPONSE.redirect(REQUEST['URL3']+'/'+new_id+'/')
            else:
                try: u=self.DestinationURL()
                except AttributeError: u=REQUEST['URL1']
                REQUEST.RESPONSE.redirect(u+'/manage_main?update_menu=1')
        else: # we're called programmatically through xx.manage_addProduct...
            return new_id

def addWikiFromZodb(self,new_id, new_title='', wiki_type='basic',
                        REQUEST=None):
    """
    Create a new zwiki web by cloning the specified template
    in /Control_Panel/Products/ZWiki
    """
    # locate the specified wiki prototype
    # these are installed in /Control_Panel/Products/ZWiki
    prototype = self.getPhysicalRoot().Control_Panel.Products.ZWiki[wiki_type]

    # clone it
    self.manage_clone(prototype, new_id, REQUEST)
    wiki = getattr(self, new_id)
    wiki.manage_changeProperties(title=new_title)
    # could do stuff with ownership here
    # set it to low-privileged "nobody" by default ?

def createFilesFromFsFolder(self, f, dir):
    """
    Recursively put the files from a fs folder into a ZODB folder.
    """
    filenames = os.listdir(dir)
    for filename in filenames:
        if re.match(r'(?:\..*|CVS|_darcs)', filename): continue
        id, type = os.path.splitext(filename)
        type = type.lstrip('.')
        this_path = os.path.join(dir, filename)
        if os.path.isdir(this_path):
            f.manage_addFolder(filename) # add folder
            createFilesFromFsFolder(self, f[filename], this_path) # recurse
        else:
            text = open(this_path, 'r').read()
            if type == 'dtml':
                addDTMLMethod(f, filename[:-5], title='', file=text)
            elif re.match(r'(?:(?:rst|stx|html|latex)(?:dtml)?|txt)', type):
                headers, body = parseHeadersBody(text)
                if headers.has_key('title'):
                    title = headers['title']
                else:
                    title = ''
                if headers.has_key('parents'):
                    parents = headers['parents']
                    parents = parents.split(',')
                else:
                    parents = []
                addZWikiPage(f,id,title=title,page_type=type,file=body,parents=parents)
            elif type == 'pt':
                f._setObject(id, ZopePageTemplate(id, text, 'text/html'))
            elif type == 'py':
                f._setObject(id, PythonScript(id))
                f._getOb(id).write(text)
            elif type == 'zexp' or type == 'xml':
                connection = self.getPhysicalRoot()._p_jar
                f._setObject(id, connection.importFile(dir + os.sep + filename))
                #self._getOb(id).manage_changeOwnershipType(explicit=0)
            elif type in ['jpg','jpeg','gif','png']:
                f._setObject(filename, Image(filename, '', text))
            else:
                id = f._setObject(filename, File(filename, '', text))
                if type == 'css': f[filename].content_type = 'text/css'

def addWikiFromFs(self, new_id, title='', wiki_type='basic',
                      REQUEST=None):
    """
    Create a new zwiki web from the specified template on the filesystem.
    """
    parent = self.Destination()
    # Go with a BTreeFolder from the start to avoid hassle with large
    # wikis on low-memory hosted servers ?
    #parent.manage_addProduct['BTreeFolder2'].manage_addBTreeFolder(
    #str(new_id),str(title))
    # No - the standard folder's UI is more useful for small wikis,
    # and more importantly BTreeFolder2 isn't standard until 2.8.0b2
    parent.manage_addFolder(str(new_id))
    f = parent[new_id]
    f.title = str(title)

    # add objects from wiki template
    # cataloging really slows this down!
    dir = os.path.join(package_home(globals()),'content',wiki_type)
    createFilesFromFsFolder(self, f, dir) # recurses
    f.objectValues(spec='ZWiki Page')[0].updatecontents()

def addZWikiPage(self, id, title='',
                  page_type=PAGETYPES[0]._id, file='', parents=[]):
    id=str(id)
    title=str(title)

    if len(parents) == 0:
        # parse optional parents list, the old way XXX can this be removed?
        m = re.match(r'(?si)(^#parents:(.*?)\n)?(.*)',file)
        if m.group(2):
            parents = string.split(string.strip(m.group(2)),',')
        else:
            parents = []
        text = m.group(3)
    else:
        text = file

    # create zwiki page in this folder
    ob = ZWikiPage.ZWikiPage(source_string=text, __name__=id)
    ob.title = title
    ob.setPageType(page_type)

    username = getSecurityManager().getUser().getUserName()
    ob.manage_addLocalRoles(username, ['Owner'])
    # the new page object is owned by the current authenticated user, if
    # any; not desirable for executable content.  Remove any such
    # ownership so that the page will acquire it's owner from the parent
    # folder.
    ob._deleteOwnershipAfterAdd() # or _owner=UnownableOwner ?
    self._setObject(id, ob)
    self[id].parents = parents # setting this earlier lost it for some pages (??)

    return getattr(self, id)


def listWikis(self):
    """
    list all wiki templates available in the filesystem or zodb
    """
    wikis = self.listFsWikis()
    for w in self.listZodbWikis():
        if not w in wikis: wikis.append(w)
    wikis.sort()
    return wikis

def listZodbWikis(self):
    """
    list the wiki templates available in the ZODB
    """
    # XXX: currently we have no idea, how to place zwiki templates
    # (like ZWiki/content/basic) into the ZODB in *Zope4*
    #
    # in *Zope2* we used to call
    #
    #    list = self.getPhysicalRoot().Control_Panel.Products.ZWiki.objectIds()
    #    list.remove('Help')
    #
    # but this doesnt work in Zope4 anymore (Control_Panel has no Products
    # attribute). So return the empty list for now.

    return []

def listFsWikis(self):
    """
    list the wiki templates available in the filesystem
    """
    try:
        list = os.listdir(package_home(globals()) + os.sep + 'content')
        # likewise for Subversion
        if '.svn' in list: list.remove('.svn')
        if 'tracker' in list: list.remove('tracker') #XXX temp
        return list
    except OSError:
        return []

