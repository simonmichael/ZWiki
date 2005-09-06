##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
# 
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
# 
##############################################################################
"""
CMF ZWiki Installation script

This file is a CMF installation script for ZWiki.  It's meant to be used
as an External Method. Compatible with the CMF quick installer, or to use
manually, add an external method to the root of the CMF or Plone Site that
you want ZWiki registered in with the configuration:

 id:            cmf_install_zwiki
 title:         
 module name:   ZWiki.Install
 function name: install

Then call this method in the context of the CMF/Plone site, by visiting
http://SITEURL/cmf_install_zwiki . The install function will execute and
give information about the steps it took.
"""

import string
from cStringIO import StringIO
from ZODB.PersistentMapping import PersistentMapping
from Products.CMFCore.TypesTool import ContentFactoryMetadata
from Products.CMFCore.DirectoryView import addDirectoryViews
from Products.CMFCore.utils import getToolByName
from Products.ZWiki.CMFInit import wiki_globals, factory_type_information
from Products.ZWiki.ZWikiPage import ZWikiPage
from Products.ZWiki.Defaults import PAGE_PORTALTYPE#,ALLOWED_PAGE_TYPES_IN_PLONE
from Products.CMFCore import CMFCorePermissions

def install(self):
    """
    Register "Wiki Page" with portal_types and friends.
    """
    out = StringIO()
    typestool = getToolByName(self, 'portal_types')
    skinstool = getToolByName(self, 'portal_skins')
    workflowtool = getToolByName(self, 'portal_workflow')
    propertiestool = getToolByName(self, 'portal_properties')
    migrationtool = getToolByName(self, 'portal_migration')
    
    # Borrowed from CMFDefault.Portal.PortalGenerator.setupTypes()
    # We loop through anything defined in the factory type information
    # and configure it in the types tool if it doesn't already exist
    for t in factory_type_information:
        if t['id'] not in typestool.objectIds():
            cfm = apply(ContentFactoryMetadata, (), t)
            typestool._setObject(t['id'], cfm)
            out.write('Registered %s with the types tool\n' % t['id'])
        else:
            out.write('Object "%s" already existed in the types tool\n' % (
                t['id']))

    # set up site catalog
    # Make sure that all the indexes and metadata that Zwiki expects from
    # a catalog are present (see setupCatalog or
    # http://zwiki.org/ZwikiAndZCatalog for a list). NB these will apply
    # for all catalogable plone objects, not just zwiki pages, but will
    # (hopefully!) be empty/harmless for the non-pages.
    ZWikiPage().__of__(self).setupCatalog()
    # this would give an even more complete catalog.. should be unnecessary
    #ZWikiPage().__of__(self).setupTracker(pages=0)

    # Setup the skins
    # This is borrowed from CMFDefault/scripts/addImagesToSkinPaths.pys
    if 'zwiki_plone' not in skinstool.objectIds():
        # We need to add Filesystem Directory Views for any directories
        # in our skins/ directory.  These directories should already be
        # configured.
        addDirectoryViews(skinstool, 'skins', wiki_globals)
        out.write("Added zwiki skin directories to portal_skins\n")

    # Now we need to go through the skin configurations and insert
    # 'zwiki_plone'.  Preferably, this should be right before where
    # 'content' is placed.  Otherwise, we append it to the end.

    # NB zwiki sometimes uses its built-in skin lookup to find helper
    # templates, searching both zwiki_ layers regardless of what's in
    # portal_skins - possible source of confusion for customizers
    # here. Should we add zwiki_standard to portal_skins for clarity ?
    # I guess so (but after zwiki_plone if already there, not custom)
    #XXX for dir in ('zwiki_standard','zwiki_plone'):
    
    skins = skinstool.getSkinSelections()
    for skin in skins:
        path = skinstool.getSkinPath(skin)
        path = map(string.strip, string.split(path,','))
        for dir in ['zwiki_plone']:
            if not dir in path:
                try:
                    idx = path.index('custom')
                except ValueError:
                    idx = 999
                path.insert(idx+1, dir)

        path = string.join(path, ', ')
        # addSkinSelection will replace existing skins as well.
        skinstool.addSkinSelection(skin, path)
        out.write("Added 'zwiki_plone' to %s skin\n" % skin)

    # And, we'll add an optional new skin, 'Zwiki', which offers Zwiki's
    # standard templates within CMF/Plone
    def hasSkin(s): return skinstool.getSkinPath(s) != s
    if not hasSkin('Zwiki'):
        path = (
            hasSkin('Plone Default') and skinstool.getSkinPath('Plone Default')
            or hasSkin('CMF Default') and skinstool.getSkinPath('CMF Default')
            or None)
        if path: # just in case
            path = map(string.strip, string.split(path,','))
            path.insert(path.index('zwiki_plone'),'zwiki_standard')
            path = string.join(path, ', ')
            skinstool.addSkinSelection('Zwiki',path)

    # remove workflow from Wiki pages
    cbt = workflowtool._chains_by_type
    if cbt is None:
        cbt = PersistentMapping()
    cbt[PAGE_PORTALTYPE] = []
    workflowtool._chains_by_type = cbt
    out.write("Removed all workflow from Wiki Page\n")

    # shouldn't need this any more
    # install an allowed_page_types property, to limit the offered page
    # types. Should maybe go in propertiestool.site_properties, zwiki
    # doesn't yet know how to check there
    ##folder = propertiestool.site_properties
    #folder = self
    #prop = 'allowed_page_types'
    #if not prop in map(lambda x:x['id'], folder._properties):
    #    folder.manage_addProperty(prop,
    #                              '\n'.join(ALLOWED_PAGE_TYPES_IN_PLONE),
    #                              'lines')
    #    out.write("Added a restricted 'allowed_page_types' site property\n")
    #else:
    #    out.write("An 'allowed_page_types' site property already exists\n")

    if(getattr(self.Control_Panel.Products, 'ExternalEditor', None) is not None):
        for ctype in typestool.objectValues():
            if ctype.getId() == 'Wiki Page':
                # We must detect plone 1 or plone 2 here because addAction has a 
                # different number of arguments
                if(migrationtool.getInstanceVersion().strip().startswith('1')):
                    ctype.addAction( 'external_edit'
                                   , name='External Edit'
                                   , action='external_edit'
                                   , permission=CMFCorePermissions.ModifyPortalContent
                                   , category='object'
                                   , visible=0 )
                elif(migrationtool.getInstanceVersion().strip().startswith('2')):
                    ctype.addAction( 'external_edit'
                                   , name='External Edit'
                                   , action='string:$object_url/external_edit'
                                   , condition=''
                                   , permission=CMFCorePermissions.ModifyPortalContent
                                   , category='object'
                                   , visible=0 )
                else:
                    out.write("Unkown Plone version!  External Editor not installed!")
                    return out.getvalue()
        out.write("External Editor is installed, added action for Wiki Page")

    return out.getvalue()

