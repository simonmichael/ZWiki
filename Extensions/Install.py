"""
Install Zwiki in a CMF or Plone site.

Normally used via Plone's Site Setup -> Add/remove products.
"""

import string
from StringIO import StringIO

from ZODB.PersistentMapping import PersistentMapping

from Products.CMFCore.DirectoryView import addDirectoryViews
from Products.CMFCore.utils import getToolByName
from Products.ZWiki.CMFInit import wiki_globals
from Products.ZWiki.ZWikiPage import ZWikiPage
from Products.ZWiki.Defaults import PAGE_PORTALTYPE
try:    from Products.CMFCore import permissions as CMFCorePermissions 
except: from Products.CMFCore import CMFCorePermissions
    

def install(self):
    out          = StringIO()
    typestool    = getToolByName(self, 'portal_types')
    skinstool    = getToolByName(self, 'portal_skins')
    workflowtool = getToolByName(self, 'portal_workflow')
    
    # register our skin layer(s) and add to each existing skin
    if 'zwiki' not in skinstool.objectIds():
        addDirectoryViews(skinstool, 'skins', wiki_globals)
    for skin in skinstool.getSkinSelections():
        path = skinstool.getSkinPath(skin)
        path = [s.strip() for s in path.split(',')]
        for layer in ['zwiki']:
            if not layer in path: path.append(layer)
        path = ', '.join(path)
        skinstool.addSkinSelection(skin, path)
        out.write("Added zwiki layer to %s skin\n" % skin)

    # ensure that all catalog indexes and metadata required for best Zwiki
    # performance are present. These will (hopefully) be harmless for
    # non-wiki page content.
    ZWikiPage().__of__(self).setupCatalog()

    # disable workflow for wiki pages
    cbt = workflowtool._chains_by_type
    if cbt is None: cbt = PersistentMapping()
    cbt[PAGE_PORTALTYPE] = []
    workflowtool._chains_by_type = cbt
    out.write("Disabled workflow on Wiki Page\n")

    # make wiki pages use External Editor, if installed, 
    if hasattr(self.Control_Panel.Products, 'ExternalEditor'):
        # XXX Uses addAction and portal_migration, which are plonisms.
        # How should we do this for vanilla CMF ? Do nothing for now.
        try:
            migrationtool = getToolByName(self, 'portal_migration')
            for ctype in typestool.objectValues():
                if ctype.getId() == 'Wiki Page':
                    # We must detect plone 1 or plone 2 here because addAction has a 
                    # different number of arguments
                    # XXX actually I'm pretty sure we don't/don't need to support plone 1
                    # any more, check
                    if(migrationtool.getInstanceVersion().strip().startswith('1')):
                        ctype.addAction( 'external_edit'
                                       , name='External Edit'
                                       , action='external_edit'
                                       , permission=CMFCorePermissions.ModifyPortalContent
                                       , category='object'
                                       , visible=0 )
                    else:
                        ctype.addAction( 'external_edit'
                                       , name='External Edit'
                                       , action='string:$object_url/external_edit'
                                       , condition=''
                                       , permission=CMFCorePermissions.ModifyPortalContent
                                       , category='object'
                                       , visible=0 )
            out.write("Enabled External Editor for Wiki Pages")
        except AttributeError:
            out.write("External Editor is installed, please add the external_edit action to Wiki Page in portal_types")

    return out.getvalue()
