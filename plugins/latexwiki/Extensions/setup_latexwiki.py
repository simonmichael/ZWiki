# setup script for a new LatexWiki site.

import os, zLOG
from Products.LatexWiki.util import workingDir
# for equations-in-ZODB
#from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2

def setup_latexwiki(self): 
    """ Add required attributes to new LatexWiki site, and then remove this method 
    """ 

    self.manage_addProperty('allow_dtml', 'true', 'boolean') 
    self.manage_addProperty('latex_font_size', 18, 'int')
    self.manage_addProperty('latex_align_fudge', 0.0, 'float')
    self.manage_addProperty('latex_res_fudge', 0.97, 'float') 
    if(not os.access(workingDir, os.F_OK)): 
        os.mkdir(workingDir)
        zLOG.LOG('LatexWiki',zLOG.DEBUG, 'LatexWiki image directory %s created'%(workingDir)) 
    id = 'images'
    # Transition to this once we are storing images in the ZODB ob =
    # BTreeFolder2(id) 
    ob = None 
    try: 
        from Products.LocalFS.LocalFS import LocalFS 
        ob = LocalFS(id, '', workingDir, None, None) 
    except ImportError: # no localfs
        zLOG.LOG('LatexWiki',zLOG.ERROR,'LocalFS not installed')
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
        zLOG.LOG('LatexWiki', zLOG.ERROR, 
            'Failed to find a suitable filesystem product')
    self.REQUEST.RESPONSE.redirect(self.REQUEST['URL1'])
    self._delObject('setup_latexwiki')


