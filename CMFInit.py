# stuff that didn't fit in CMF.py or __init__.py

from types import *
import string, re, os
from AccessControl import getSecurityManager
from DateTime import DateTime
from Globals import package_home
from ZWikiPage import ZWikiPage
import Permissions
from Defaults import PAGE_METATYPE, PAGE_PORTALTYPE
from ZWikiWeb import _addDTMLMethod, _addZWikiPage

wiki_globals=globals()

default_perms = {
    'create': 'nonanon',
    'edit': 'nonanon',
    'comment': 'nonanon',
    'move': 'owners', # rename/delete/reparent
    'regulate': 'owners'
    }

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
    {'id': PAGE_PORTALTYPE,
     'content_icon': 'wikipage_icon.gif',
     'meta_type': PAGE_METATYPE,
     'product': 'ZWiki',
     'factory': 'addWikiPage',
     'immediate_view': 'wikipage_view',

     # Following latest cmf/plone practice, some of these are "views",
     # some are "actions".. I must say I find the distinction rather murky
     # for these. Also, some are definitely views/actions for the folder
     # (wiki) rather than the object (page), and if there was a folder
     # views/actions category they would go there. Or in a single-wiki
     # site, you probably want to put them in the portal_tabs category.
     'actions': ({'id': 'view',
                  'name': 'View',
                  'action': 'wikipage_view',
                  'permissions': (Permissions.View,),
                  'category': 'object',
                  },
                 {'id': 'edit',
                  'name': 'Edit',
                  'action': 'editform',
                  'permissions': (Permissions.Edit,),
                  'category': 'object',
                  },
                 {'id': 'history',
                  'name': 'History',
                  'action': 'diff',
                  'permissions': (Permissions.View,),
                  'category': 'object',
                  },
                 {'id': 'backlinks',
                  'name': 'Backlinks',
                  'action': 'backlinks',
                  'permissions': (Permissions.View,),
                  'category': 'object',
                  },
                 {'id': 'subscribe',
                  'name': 'Subscribe',
                  'action': 'subscribeform',
                  'permissions': (Permissions.View,),
                  'condition': 'object/isMailoutEnabled',
                  'category': 'object',
                  },
                 {'id': 'contents',
                  'name': 'Wiki contents',
                  'action': 'python:object.contentsUrl()',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  },
                 {'id': 'recentchanges',
                  'name': 'Wiki changes',
                  'action': 'recentchanges',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  },
                 {'id': 'issuetracker',
                  'name': 'Issue tracker',
                  'action': 'issuetracker',
                  'permissions': (Permissions.View,),
                  'condition': 'object/hasIssues',
                  'category': 'object_actions',
                  },
                 {'id': 'filterissues',
                  'name': 'Filter issues',
                  'action': 'filterissues',
                  'permissions': (Permissions.View,),
                  'condition': 'object/hasIssues',
                  'category': 'object_actions',
                  },
                 {'id': 'searchwiki',
                  'name': 'Search this wiki',
                  'action': 'searchwiki',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  },
                 {'id': 'useroptions',
                  'name': 'Wiki options',
                  'action': 'useroptions',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  'visible': 0,
                  },
                 ),
     },
    )

from Products.CMFCore import utils
from Products.CMFCore.DirectoryView import registerDirectory

def initialize(context): 
    """Initialize the ZWiki product for use in CMF.
    """
    registerDirectory('skins', globals())
    # XXX I don't want this in the zmi add menu, how can I hide it ?
    utils.ContentInit(
        'Wiki Content',
        content_types = (ZWikiPage, ),
        permission = Permissions.Add,
        extra_constructors = (addWikiPage, ),
        fti = factory_type_information,
        ).initialize(context)
