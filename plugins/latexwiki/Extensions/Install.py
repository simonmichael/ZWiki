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

This file is a CMF installation script for LatexWiki.  It's meant to be used
as an External Method. Compatible with the CMF quick installer, or to use
manually, add an external method to the root of the CMF or Plone Site that
you want LatexWiki registered in with the configuration:

 id:            cmf_install_latexwiki
 title:         
 module name:   LatexWiki.Install
 function name: install

Then call this method in the context of the CMF/Plone site, by visiting
http://SITEURL/cmf_install_latexwiki . The install function will execute and
give information about the steps it took.
"""

import string, os, sys
from Products.LatexWiki.util import workingDir
from cStringIO import StringIO
from OFS.DTMLMethod import DTMLMethod
from OFS.Image import Image, File
from OFS.ObjectManager import customImporters
from ZODB.PersistentMapping import PersistentMapping
from Products.CMFCore.TypesTool import ContentFactoryMetadata
from Products.CMFCore.DirectoryView import addDirectoryViews
from Products.CMFCore.utils import getToolByName
from Products.ZWiki.CMFInit import wiki_globals, factory_type_information
from Products.ZWiki.ZWikiPage import ZWikiPage
from Products.ZWiki.ZWikiWeb import _addDTMLMethod
from Products.ZWiki.Defaults import PAGE_PORTALTYPE#,ALLOWED_PAGE_TYPES_IN_PLONE


def install(self):
    """
    Create images directory and add some necessary properties to the folder.
    """
    out = StringIO()
    out.write('Adding properties to folder\n')
    if not self.hasProperty('allow_dtml'):
        self.manage_addProperty('allow_dtml', 'true', 'boolean') 
    if not self.hasProperty('latex_font_size'):
        self.manage_addProperty('latex_font_size', 18, 'int')
    if not self.hasProperty('latex_align_fudge'):
        self.manage_addProperty('latex_align_fudge', 0.0, 'float')
    if not self.hasProperty('latex_res_fudge'):
        self.manage_addProperty('latex_res_fudge', 1.00, 'float') 
    if(not os.access(workingDir, os.F_OK)): 
        os.mkdir(workingDir)
        out.write('LatexWiki image directory %s created'%(workingDir)) 
    id = 'images'
    # Transition to this once we are storing images in the ZODB ob =
    # BTreeFolder2(id) 
    ob = None 
    try: 
        from Products.LocalFS.LocalFS import LocalFS 
        ob = LocalFS(id, '', workingDir, None, None) 
    except ImportError: # no localfs
        out.write('Error: LocalFS not installed.  LatexWiki requires LocalFS.')
# FileSystemSite does not automatically refresh when the contents of the
# filesystem chages.  I'm not sure if it's possible to enable that...
#        try:
#            from Products.FileSystemSite.DirectoryView import DirectoryView
#            ob = DirectoryView(id, workingDir)
#        except ImportError:
#            zLOG.LOG('LatexWiki',zLOG.DEBUG,'FileSystemSite not installed either')
    # FIXME: try Ape too
    if ob != None:
        self._setObject(id, ob, set_owner=1)
    else:
        out.write('ERROR: Failed to find a suitable filesystem product')

    filename = 'latexwiki.css.dtml'
    dir = sys.modules['__builtin__'].SOFTWARE_HOME + os.sep \
          + 'Products/ZWiki/content/latexwiki'
    if(not os.access(dir, os.F_OK)):
        dir = sys.modules['__builtin__'].INSTANCE_HOME + os.sep \
              + 'Products/ZWiki/content/latexwiki'
    text = open(dir + os.sep + filename).read()
    _addDTMLMethod(self, 'latexwiki.css', title='', file=text)
    filename = 'blank.gif.gif'
    text = open(dir + os.sep + filename).read()
    self._setObject('blank.gif', Image('blank.gif', '', text))
    filename = 'pngbehavior.htc.zexp'
    connection = self.getPhysicalRoot()._p_jar
    self._setObject('pngbehavior.htc', connection.importFile(dir + os.sep + filename, 
        customImporters=customImporters))
    id = 'ploneCustom.css'
    if hasattr(self,id):
        ploneCustom = self._getOb(id)
        self._setObject(id, File(id, '', '@import url("latexwiki.css");'))
    else:
        text = ploneCustom.text() 
        if(not re.match(r'@import url\("latexwiki.css"\);', text)):
            text = text + '\n@import url("latexwiki.css");';
        ploneCustom.write(text)
    return out.getvalue()

