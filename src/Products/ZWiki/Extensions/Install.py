"""
Install Zwiki in a CMF or Plone site.

Normally used via Plone's Site Setup -> Add/remove products.
"""

from StringIO import StringIO
from ZODB.PersistentMapping import PersistentMapping
from Products.CMFCore.DirectoryView import addDirectoryViews
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions

from Products.ZWiki.ZWikiPage import ZWikiPage
from Products.ZWiki.Defaults import PAGE_PORTALTYPE
from Products.ZWiki.Utils import safe_hasattr

def install(portal):
    out          = StringIO()
    portal_types    = getToolByName(portal, 'portal_types')
    portal_skins    = getToolByName(portal, 'portal_skins')
    portal_workflow = getToolByName(portal, 'portal_workflow')
    portal_setup = getToolByName(portal, 'portal_setup')

    portal_setup.runAllImportStepsFromProfile('profile-ZWiki:default')

    # XXX move the following into the profile above.. cf
    # http://dev.plone.org/plone/browser/CMFPlone/trunk/profiles/default/types/Discussion_Item.xml

    # register our skin layer(s) and add to each existing skin
    if 'zwiki' not in portal_skins.objectIds():
        addDirectoryViews(portal_skins, 'skins', {'__name__':'Products.ZWiki'})
    for skin in portal_skins.getSkinSelections():
        path = portal_skins.getSkinPath(skin)
        path = [s.strip() for s in path.split(',')]
        for layer in ['zwiki']:
            if not layer in path: path.append(layer)
        path = ', '.join(path)
        portal_skins.addSkinSelection(skin, path)
        out.write("Added zwiki layer to %s skin\n" % skin)

    # ensure that all catalog indexes and metadata required for best Zwiki
    # performance are present. These will (hopefully) be harmless for
    # non-wiki page content.
    ZWikiPage().__of__(portal).setupCatalog()

    # disable workflow for wiki pages
    cbt = portal_workflow._chains_by_type
    if cbt is None: cbt = PersistentMapping()
    cbt[PAGE_PORTALTYPE] = []
    portal_workflow._chains_by_type = cbt
    out.write("Disabled workflow on Wiki Page\n")

    # make wiki pages use External Editor, if installed,
    if safe_hasattr(portal.Control_Panel.Products, 'ExternalEditor'):
        # XXX Uses addAction and portal_migration, which are plonisms.
        # How should we do this for vanilla CMF ? Do nothing for now.
        try:
            migrationtool = getToolByName(portal, 'portal_migration')
            for ctype in portal_types.objectValues():
                if ctype.getId() == 'Wiki Page':
                    # We must detect plone 1 or plone 2 here because addAction has a
                    # different number of arguments
                    # XXX actually I'm pretty sure we don't/don't need to support plone 1
                    # any more, check
                    if(migrationtool.getInstanceVersion().strip().startswith('1')):
                        ctype.addAction( 'external_edit'
                                       , name='External Edit'
                                       , action='external_edit'
                                       , permission=permissions.ModifyPortalContent
                                       , category='object'
                                       , visible=0 )
                    else:
                        ctype.addAction( 'external_edit'
                                       , name='External Edit'
                                       , action='string:$object_url/external_edit'
                                       , condition=''
                                       , permission=permissions.ModifyPortalContent
                                       , category='object'
                                       , visible=0 )
            out.write("Enabled External Editor for Wiki Pages")
        except AttributeError:
            out.write("External Editor is installed, please add the external_edit action to Wiki Page in portal_types")

    return out.getvalue()

def uninstall(portal):
    portal_setup = getToolByName(portal, 'portal_setup')
    portal_setup.runAllImportStepsFromProfile('profile-ZWiki:uninstall')
    return "Ran all uninstall steps."

