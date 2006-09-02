# stuff that didn't fit in CMF.py or __init__.py
# __init__ tries to import this, will ignore any errors

from types import *
import string, re, os
from AccessControl import getSecurityManager
from DateTime import DateTime
import Products.CMFCore
from Products.CMFCore.DirectoryView import registerDirectory

from ZWikiPage import ZWikiPage
import Permissions
from Defaults import PAGE_METATYPE, PAGE_PORTALTYPE
from Wikis import _addDTMLMethod, _addZWikiPage
from I18n import _

# no longer used, but maybe later.
try:
    import Products.CMFPlone
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
    {'id': PAGE_PORTALTYPE,
     'content_icon': 'wikipage_icon.gif',
     'meta_type': PAGE_METATYPE,
     'product': 'ZWiki',
     'factory': 'addWikiPage',
     'immediate_view': '',

     # Following latest cmf/plone practice, some of these are "views",
     # some are "actions".. I must say I find the distinction rather murky
     # for these. Also, some are definitely views/actions for the folder
     # (wiki) rather than the object (page), and if there was a folder
     # views/actions category they would go there. Or in a single-wiki
     # site, you probably want to put them in the portal_tabs category.
     'actions': ({'id': 'view',
                  'name': 'View',
                  'action': '',
                  'permissions': (Permissions.View,),
                  'category': 'object',
                  },
                 {'id': 'edit',
                  'name': 'Edit',
                  'action': 'editform',
                  'permissions': (Permissions.Edit,),
                  'category': 'object',
                  },
                 {'id': 'subscribe',
                  'name': 'Subscribe',
                  'action': 'subscribeform',
                  'permissions': (Permissions.View,),
                  'condition': 'object/isMailoutEnabled',
                  'category': 'object',
                  },
                 {'id': 'history',
                  'name': 'history',
                  'action': 'diff',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  },
                 {'id': 'backlinks',
                  'name': 'Related pages',
                  'action': 'backlinks',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  },
                 {'id': 'recentchanges',
                  'name': 'Wiki changes',
                  'action': 'python:object.changesUrl()',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  },
                 {'id': 'contents',
                  'name': 'Wiki contents',
                  'action': 'python:object.contentsUrl()',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  },
                 {'id': 'issuetracker',
                  'name': 'Issues',
                  'action': 'python:object.trackerUrl()',
                  'permissions': (Permissions.View,),
                  'condition': 'object/hasIssues',
                  'category': 'object_actions',
                  },
                 # hidden by default
                 {'id': 'searchwiki',
                  'name': 'Wiki search',
                  'action': 'python:object.searchUrl()',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  'visible': 0,
                  },
                 {'id': 'useroptions',
                  'name': 'Wiki options',
                  'action': 'python:object.preferencesUrl()',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  'visible': 0,
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
