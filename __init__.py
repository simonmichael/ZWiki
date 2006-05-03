# product initialization

__doc__="""
ZWiki product
"""
__version__='0.53.0'

import os, re
from os import path
import Globals, OFS.Folder
from Globals import MessageDialog
import ZWikiPage, Wikis, Permissions, Defaults, OutlineSupport
from I18n import _

misc_ = {
    'ZWikiPage_icon': Globals.ImageFile(
        path.join('skins','zwiki','wikipage_icon.gif'), globals()),
    # backwards compatibility
    'ZWikiPage_icon.gif': Globals.ImageFile(
        path.join('skins','zwiki','wikipage_icon.gif'),globals()),
    # for the rating plugin
    'star_icon': Globals.ImageFile(
        path.join('skins','zwiki','star.png'),globals()),
    'blank_star_icon': Globals.ImageFile(
        path.join('skins','zwiki','blank_star.png'),globals()),
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
            OFS.Folder.Folder,
            meta_type=Defaults.WIKI_ADD_MENU_NAME,
            permission=Permissions.AddWiki,
            #icon = 'images/Wiki_icon.gif'
            constructors = ( 
                Wikis.manage_addWikiForm,
                Wikis.manage_addWiki,
                Wikis.listWikis,
                Wikis.listZodbWikis,
                Wikis.listFsWikis,
                Wikis.addWikiFromFs,
                Wikis.addWikiFromZodb,
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

#def autoImport(context):
#    """Import any files in our import directory
#       into /Control_Panel/Products/PRODUCT.
#       Called at product startup and refresh.
#       XXX auto-refresh too ?
#
#       How to handle versions & upgrades of imported content nicely ?
#       Don't want to overwrite anything the zope admin has in place.
#       Try to KISS..
#       
#       Here's the plan for zwiki: sample wiki zexp filenames will end
#       in a version number corresponding to the zwiki release they
#       shipped with (eg). The imported id is based on this so newer
#       versions will import cleanly. The Add Zwiki Web form will use
#       the latest version of each sample wiki that it finds. The admin
#       can clean out old versions at will.
#       """
#
#    importdir = Globals.package_home(globals()) + os.sep + 'import'
#    if 0: #XXX not exists(importdir)
#        return
#
#    # sneaky, or dumb, way to get to the zodb
#    obj = context.getProductHelp()
#    productfolder = obj.getPhysicalRoot().Control_Panel.Products['ZWiki']
#                                #XXX should find product name dynamically
#
#    # based on manage_importObject
#    # locate a valid connection
#    connection=obj._p_jar
#    while connection is None:
#        obj=obj.aq_parent
#        connection=obj._p_jar
#
#    # try to import any and all files found
#    # will fail if the object is already in the ZODB
#    files = os.listdir(importdir)  
#    for filename in files:
#        filepath = importdir + os.sep + filename
#        # how do we get these to show in undo ?
#        #get_transaction().begin()
#        try:
#            ob=connection.importFile(filepath, customImporters=customImporters)
#            id = filename[:-5]  # assume files are named something.zexp
#            productfolder._setObject(id, ob, set_owner=0)
#            
#            # try to make ownership implicit if possible
#            ob=productfolder._getOb(id)
#            ob.manage_changeOwnershipType(explicit=0)
#            #get_transaction().commit()
#            #XXX log it
#            
#        except:
#            #get_transaction().abort()
#            #XXX log it
#            pass

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
