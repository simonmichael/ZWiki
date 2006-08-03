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

    # Set up the skins
    if 'zwiki' not in skinstool.objectIds():
        addDirectoryViews(skinstool, 'skins', wiki_globals)

    # add the zwiki skin layer to each existing skin
    # XXX should also remove old zwiki_plone, zwiki_standard layers
    skins = skinstool.getSkinSelections()
    for skin in skins:
        path = skinstool.getSkinPath(skin)
        path = map(string.strip, string.split(path,','))
        for dir in ['zwiki']:
            if not dir in path:
                try:
                    idx = path.index('custom')
                except ValueError:
                    idx = 999
                path.insert(idx+1, dir)
        path = string.join(path, ', ')
        # addSkinSelection will replace existing skins as well.
        skinstool.addSkinSelection(skin, path)
        out.write("Added zwiki layer to %s skin\n" % skin)

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


    # if External Editor is installed, make sure Wiki Pages have the
    # external edit action.
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
            out.write("External Editor is installed, added the action to Wiki Page")
        except AttributeError:
            out.write("External Editor is installed, please add the external_edit action to Wiki Page in portal_types")

    return out.getvalue()

