# product initialization

__doc__="""
ZWiki product
"""
__version__='0.37.0rc1'

import os, re
from os import path
import Globals, OFS.Folder
#XXX import pagetypes
import ZWikiPage, ZWikiWeb, Permissions, Defaults

misc_ = {
    'ZWikiPage_icon': Globals.ImageFile(path.join('images','ZWikiPage_icon.gif'),
                                   globals()),
    'star_icon': Globals.ImageFile(path.join('images','star.png'),
                                   globals()),
    'blank_star_icon': Globals.ImageFile(path.join('images','blank_star.png'),
                                   globals()),
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
            icon = 'images/ZWikiPage_icon.gif',
            constructors = ( 
                ZWikiPage.manage_addZWikiPageForm,
                ZWikiPage.manage_addZWikiPage,
                ),
            )
        # allow zclass subclassing
        #context.createZClassForBase(ZWikiPage.ZWikiPage,
        #                              globals(),
        #                              nice_name=None)
        # set up an "add wiki" menu item
        context.registerClass(
            OFS.Folder.Folder,
            meta_type=Defaults.WIKI_ADD_MENU_NAME,
            permission=Permissions.AddWiki,
            #icon = 'images/ZWikiWeb_icon.gif'
            constructors = ( 
                ZWikiWeb.manage_addZWikiWebForm,
                ZWikiWeb.manage_addZWikiWeb,
                ZWikiWeb.listWikis,
                ZWikiWeb.listZodbWikis,
                ZWikiWeb.listFsWikis,
                ZWikiWeb.addZWikiWebFromFs,
                ZWikiWeb.addZWikiWebFromZodb,
                )
            )
        # do CMF initialisation if installed
        try:
            import CMFInit
            CMFInit.initialize(context)
        except ImportError:
            pass
        # also register skin dirs with FileSystemSite if installed
        try:
            from Products.FileSystemSite.DirectoryView import registerDirectory
            registerDirectory('skins', globals())
        except ImportError:
            pass
        # auto-install extra wiki templates to zodb
        #autoImport(context)

    except:
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

# set up catalog awareness for ZMI operations, do it here to avoid import loop
# XXX warning, manage_renameObject will lose parentage in the wiki outline
def manage_afterAdd(self, item, container):
    self.setCreator(getattr(self,'REQUEST',None)) # save creation info
    self.wikiOutline().add(self.pageName()) # update the wiki outline
    self.index_object()
ZWikiPage.ZWikiPage.manage_afterAdd = manage_afterAdd

def manage_afterClone(self, item):
    self.setCreator(getattr(self,'REQUEST',None)) # save creation info
    self.wikiOutline().add(self.pageName()) # update the wiki outline
    self.index_object()
ZWikiPage.ZWikiPage.manage_afterClone = manage_afterClone

def manage_beforeDelete(self, item, container):
    # update the wiki outline, but if it's out of date just ignore
    try: self.wikiOutline().delete(self.pageName())
    except KeyError: pass
    self.unindex_object()
ZWikiPage.ZWikiPage.manage_beforeDelete = manage_beforeDelete

#original_edit = ZWikiPage.ZWikiPage.manage_edit
#def manage_edit(self,data,title,SUBMIT='Change',dtpref_cols='50',
#                dtpref_rows='20',REQUEST=None):
#    """Edit object an reindex"""
#    r = original_edit(self,data,title,SUBMIT,dtpref_cols,dtpref_rows,REQUEST)
#    self.reindex_object()
#    return r
#ZWikiPage.ZWikiPage.manage_edit = manage_edit

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
    #r = original_changeProperties(self, REQUEST, **kw)
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
