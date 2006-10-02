"""
Creating new wikis, from a list of wiki templates (just one right now).
"""

import os, os.path, re, string, urllib

from Globals import package_home, MessageDialog
from OFS.Folder import Folder
from OFS.DTMLMethod import DTMLMethod
from AccessControl import getSecurityManager
from OFS.Image import Image, File
from OFS.ObjectManager import customImporters
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PythonScripts.PythonScript import PythonScript
from pagetypes import PAGETYPES, PAGE_TYPES
from I18n import DTMLFile, _
from ZWikiPage import ZWikiPage


# ZMI wiki creation form
manage_addWikiForm = DTMLFile('skins/zwiki/addwikiform', globals())

######################################################################
# FUNCTION CATEGORY: wikiweb creation
######################################################################

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
        #why do this ?
        #else:
        #    return ''

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
            f._setObject(id, Image(id, '', text))
        else:
            f._setObject(id, File(id, '', text))

def addDTMLMethod(self, id, title='', file=''):
    id=str(id)
    title=str(title)
    ob = DTMLMethod(source_string=file, __name__=id)
    ob.title = title
    username = getSecurityManager().getUser().getUserName()
    ob.manage_addLocalRoles(username, ['Owner'])
    #ob.setSubOwner('both') #?
    self._setObject(id, ob)

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
    ob = ZWikiPage(source_string=text, __name__=id)
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

