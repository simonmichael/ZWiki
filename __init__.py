# product initialization

__doc__="""
ZWiki product
"""
__version__='0.59.0'

import os, re, os.path, string, urllib

from AccessControl import getSecurityManager
from Globals import package_home, MessageDialog, ImageFile
from OFS.Folder import Folder
from OFS.Image import Image, File
from OFS.ObjectManager import customImporters
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PythonScripts.PythonScript import PythonScript

import Admin, Defaults, OutlineSupport, Permissions, ZWikiPage
from Admin import addDTMLMethod
from I18n import _, DTMLFile
from pagetypes import PAGETYPES


misc_ = {
    'ZWikiPage_icon': ImageFile(os.path.join('skins','zwiki','wikipage_icon.gif'), globals()),
    # backwards compatibility
    'ZWikiPage_icon.gif': ImageFile(os.path.join('skins','zwiki','wikipage_icon.gif'),globals()),
    # for the rating plugin
    'star_icon': ImageFile(os.path.join('skins','zwiki','star.png'),globals()),
    'blank_star_icon': ImageFile(os.path.join('skins','zwiki','blank_star.png'),globals()),
    }

def dummyOutlineConstructor(self):
    """Stub so we can get PersistentOutline registered with ZMI.

    The real constructor is a zwikipage method and is called automatically.
    """
    return MessageDialog(
        title=_("No need to add a Zwiki Outline Cache"),
        message=_("""Zwiki Outline Cache appears in the ZMI Add menu
        for implementation reasons, but should not be added directly.
        Zwiki will create it for you as needed.
        """))

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
        # and the PersistentOutline class, so it's zmi-manageable
        context.registerClass(
            OutlineSupport.PersistentOutline,
            permission=Permissions.manage_properties,
            #icon = 'images/ZWikiPage_icon.gif',
            constructors = (
                dummyOutlineConstructor,
                ),
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
        # do CMF initialisation if installed
        try:
            import CMFInit
            CMFInit.initialize(context)
        except ImportError:
            pass
        # register skin as customizable dir if FileSystemSite is installed
        try:
            from Products.FileSystemSite.DirectoryView import registerDirectory
            registerDirectory('skins/zwiki', globals())
        except ImportError:
            pass

    # don't let any error prevent initialisation
    except:
        # log it
        import sys, traceback, string
        type, val, tb = sys.exc_info()
        sys.stderr.write(string.join(traceback.format_exception(type, val, tb),
                                     ''))
        del type, val, tb


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

def manage_addWiki(self, new_id, new_title='', wiki_type='zwikidotorg',
                       REQUEST=None, enter=0):
    """
    Create a new zwiki web of the specified type
    """
    if not REQUEST: REQUEST = self.REQUEST
    
    # check for a configuration wizard
    if hasattr(self,wiki_type+'_config'):
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
            return MessageDialog(
                title=_('Unknown wiki type'),
                message='',
                action=''
                )

        if REQUEST is not None:
            folder = getattr(self, new_id)
            if hasattr(folder, 'setup_%s'%(wiki_type)):
                REQUEST.RESPONSE.redirect(REQUEST['URL3']+'/'+new_id+'/setup_%s'%(wiki_type))
            elif enter:
                # can't see why this doesn't work after addWikiFromFs
                #REQUEST.RESPONSE.redirect(getattr(self,new_id).absolute_url())
                REQUEST.RESPONSE.redirect(REQUEST['URL3']+'/'+new_id+'/')
            else:
                try: u=self.DestinationURL()
                except: u=REQUEST['URL1']
                REQUEST.RESPONSE.redirect(u+'/manage_main?update_menu=1')

def addWikiFromZodb(self,new_id, new_title='', wiki_type='zwikidotorg',
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


def addWikiFromFs(self, new_id, title='', wiki_type='zwikidotorg',
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
    f = Folder()
    f.id, f.title = str(new_id), str(title)
    new_id = parent._setObject(f.id, f)
    f = parent[new_id]
    # add objects from wiki template
    # cataloging really slows this down!
    dir = os.path.join(package_home(globals()),'wikis',wiki_type)
    filenames = os.listdir(dir)
    for filename in filenames:
        if re.match(r'(?:\..*|CVS|_darcs)', filename): continue
        m = re.search(r'(.+)\.(.+)',filename)
        id, type = filename, ''
        if m: id, type = m.groups()
        text = open(dir + os.sep + filename, 'r').read()
        if type == 'dtml':
            addDTMLMethod(f, filename[:-5], title='', file=text)
        elif re.match(r'(?:(?:stx|html|latex)(?:dtml)?|txt)', type):
            addZWikiPage(f,id,title='',page_type=type,file=text)
        elif type == 'pt':
            f._setObject(id, ZopePageTemplate(id, text, 'text/html'))
        elif type == 'py':
            f._setObject(id, PythonScript(id))
            f._getOb(id).write(text)
        elif type == 'zexp' or type == 'xml':
            connection = self.getPhysicalRoot()._p_jar
            f._setObject(id, connection.importFile(dir + os.sep + filename, 
                customImporters=customImporters))
            #self._getOb(id).manage_changeOwnershipType(explicit=0)
        elif re.match(r'(?:jpe?g|gif|png)', type):
            f._setObject(filename, Image(filename, '', text))
        else:
            id = f._setObject(filename, File(filename, '', text))
            if type == 'css': f[filename].content_type = 'text/css'
    f.objectValues(spec='ZWiki Page')[0].updatecontents()

def addZWikiPage(self, id, title='',
                  page_type=PAGETYPES[0]._id, file=''):
    id=str(id)
    title=str(title)

    # parse optional parents list
    m = re.match(r'(?si)(^#parents:(.*?)\n)?(.*)',file)
    if m.group(2):
        parents = string.split(string.strip(m.group(2)),',')
    else:
        parents = []
    text = m.group(3)

    # create zwiki page in this folder
    ob = ZWikiPage.ZWikiPage(source_string=text, __name__=id)
    ob.title = title
    ob.setPageType(page_type)
    ob.parents = parents

    username = getSecurityManager().getUser().getUserName()
    ob.manage_addLocalRoles(username, ['Owner'])
    # the new page object is owned by the current authenticated user, if
    # any; not desirable for executable content.  Remove any such
    # ownership so that the page will acquire it's owner from the parent
    # folder.
    ob._deleteOwnershipAfterAdd() # or _owner=UnownableOwner ?
    #ob.setSubOwner('both') # regulations setup ?
    self._setObject(id, ob)

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
    list = self.getPhysicalRoot().Control_Panel.Products.ZWiki.objectIds()
    list.remove('Help')
    return list
    
def listFsWikis(self):
    """
    list the wiki templates available in the filesystem
    """
    try:
        list = os.listdir(package_home(globals()) + os.sep + 'wikis')
        # likewise for Subversion
        if '.svn' in list: list.remove('.svn')
        if 'tracker' in list: list.remove('tracker') #XXX temp
        return list
    except OSError:
        return []

