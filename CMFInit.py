# stuff that didn't fit in CMF.py or __init__.py
# __init__ tries to import this, will ignore any errors

from types import *
import string, re, os
from AccessControl import getSecurityManager
from DateTime import DateTime
import Products.CMFCore.utils
from Products.CMFCore.DirectoryView import registerDirectory

from ZWikiPage import ZWikiPage
import Permissions
from Defaults import PAGE_METATYPE, PAGE_PORTALTYPE
from I18n import _

# no longer used, but maybe later.
try:
    import Products.CMFPlone.utils
    PLONE_VERSION = Products.CMFPlone.utils.getFSVersionTuple()
except ImportError:
    PLONE_VERSION = (0,0,0) # not installed

default_perms = {
    'create': 'nonanon',
    'edit': 'nonanon',
    'comment': 'nonanon',
    'move': 'owners', # rename/delete/reparent
    'regulate': 'owners'
    }

wiki_globals=globals()

registerDirectory('skins', wiki_globals)

def initPageMetadata(page):
    page.creation_date = DateTime()
    page._editMetadata(title='',
                       subject=(),
                       description='',
                       contributors=(),
                       effective_date=None,
                       expiration_date=None,
                       format='text_html',
                       language='',
                       rights = '')

def makeWikiPage(id, title, file):
    ob = ZWikiPage(source_string=file, __name__=id)
    ob.title = title
    ob.parents = []
    username = getSecurityManager().getUser().getUserName()
    ob.manage_addLocalRoles(username, ['Owner'])
    #ob._getRegs().setSubOwner('both')
    initPageMetadata(ob)
    #XXX sets up default permissions/regulations
    #for name, perm in ob._perms.items():
    #    pseudoperm = default_perms[name]
    #    local_roles_map = ob._local_roles_map
    #    roles_map = ob._roles_map
    #    roles = (local_roles_map[name],) + roles_map[pseudoperm]
    #    ob.manage_permission(perm, roles=roles)
    return ob

def addWikiPage(self, id, title='', page_type=None, file=''):
    id=str(id)
    title=str(title)
    ob = makeWikiPage(id, title, file)
    ob.setPageType(
        page_type or getattr(self,'allowed_page_types',[None])[0])
    self._setObject(id, ob)

factory_type_information = (
    {
     'id':             PAGE_PORTALTYPE,
     'meta_type':      PAGE_METATYPE,
     'content_icon':   'wikipage_icon.gif',
     'product':        'ZWiki',
     'factory':        'addWikiPage',
     'immediate_view': '',
     'actions':        (
                        {
                         'name'        : 'View',
                         'id'          : 'view',
                         'action'      : '',
                         'permissions' : (Permissions.View,),
                         'category'    : 'object',
                         },
                        {
                         'name'        : 'Edit',
                         'id'          : 'edit',
                         'action'      : 'editform',
                         'permissions' : (Permissions.Edit,),
                         'category'    : 'object',
                         },
                        {
                         'name'        : 'Subscribe',
                         'id'          : 'subscribe',
                         'action'      : 'subscribeform',
                         'permissions' : (Permissions.View,),
                         'condition'   : 'object/isMailoutEnabled',
                         'category'    : 'object',
                         },

                        # NB object_actions actions display in reverse order!
                        # (last will be left-most)
                        {
                         'visible'     : 0,
                         'name'        : 'Wiki options',
                         'id'          : 'useroptions',
                         'action'      : 'python:object.preferencesUrl()',
                         'permissions' : (Permissions.View,),
                         'category'    : 'object_actions',
                         },
                        {
                         'visible'     : 0,
                         'name'        : 'Wiki search',
                         'id'          : 'searchwiki',
                         'action'      : 'python:object.searchUrl()',
                         'permissions' : (Permissions.View,),
                         'category'    : 'object_actions',
                         },
                        {
                         'name'        : 'Issue pages',
                         'id'          : 'issuetracker',
                         'action'      : 'python:object.trackerUrl()',
                         'permissions' : (Permissions.View,),
                         'condition'   : 'object/hasIssues',
                         'category'    : 'object_actions',
                         },
                        {
                         'name'        : 'Wiki changes',
                         'id'          : 'recentchanges',
                         'action'      : 'python:object.changesUrl()',
                         'permissions' : (Permissions.View,),
                         'category'    : 'object_actions',
                         },
                        {
                         'name'        : 'Wiki contents',
                         'id'          : 'contents',
                         'action'      : 'python:object.contentsUrl()',
                         'permissions' : (Permissions.View,),
                         'category'    : 'object_actions',
                         },
                        {
                         'name'        : 'Related pages',
                         'id'          : 'backlinks',
                         'action'      : 'backlinks',
                         'permissions' : (Permissions.View,),
                         'category'    : 'object_actions',
                         },
                        {
                         'name'        : 'History',
                         'id'          : 'history',
                         'action'      : 'diff',
                         'permissions' : (Permissions.View,),
                         'category'    : 'object_actions',
                         },
                        ),
     },
    )


def initialize(context): 
    """Initialize the ZWiki product for use in CMF.
    """
    registerDirectory('skins', globals())
    # XXX I don't want this in the zmi add menu, how can I hide it ?
    Products.CMFCore.utils.ContentInit(
        'Wiki Content',
        content_types = (ZWikiPage, ),
        permission = Permissions.Add,
        extra_constructors = (addWikiPage, ),
        fti = factory_type_information,
        ).initialize(context)
