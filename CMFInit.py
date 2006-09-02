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

# The metadata tab broke in plone 2.5 because, as I understand it,
# plone dropped the metadata_edit_form template in favour of a properties
# method; so the action needs to link to /properties with plone >= 2.5,
# and to /metadata_edit_form with plone <2.5 or non-plone cmf.
# I decided to disable the tab by default, but we still create the action
# it should work if people enable it. Issues to resolve:
#
# 1. be off by default
#    use visible: 0
#    
# 2. handle existing sites & upgrades gracefully
#
#    a. when upgrading zwiki, in a site which has had
#       the metadata tab installed, it will remain
#       visible. Tell admins to uncheck visible in
#       portal_types -> Wiki Page -> actions, or
#       remove/add Zwiki in the site. (check this)
#
#    b. when upgrading plone past 2.5, clicking on
#       the metadata tab on wiki pages will give an
#       error. Tell admins to remove/add Zwiki in the
#       site.
#       
# 3. be easy to enable
#    check visible box in portal_types -> Wiki Page -> actions
#    -> properties (metadata ?) action
# 
# 4. work in all plones
#    add appropriate action for current plone version,
#    tell admins to remove/add Zwiki when upgrading plone past 2.5

if PLONE_VERSION >= (2,5):                 
    METADATA_TAB = {'id': 'properties',
                    'name': 'Properties',
                    'action': 'string:${object_url}/properties',
                    'permissions': (Permissions.Edit,),
                    'category': 'object',
                    'visible': 0,
                    }
else:
    METADATA_TAB = {'id': 'metadata',
                    'name': 'Metadata',
                    'action': 'string:${object_url}/metadata_edit_form',
                    'permissions': (Permissions.Edit,),
                    'category': 'object',
                    'visible': 0,
                    }

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
                 {'id': 'recentchanges',
                  'name': 'Recent changes',
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
                 {'id': 'searchwiki',
                  'name': 'Wiki search',
                  'action': 'python:object.searchUrl()',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  },
                 {'id': 'issuetracker',
                  'name': 'Issue tracker',
                  'action': 'python:object.trackerUrl()',
                  'permissions': (Permissions.View,),
                  'condition': 'object/hasIssues',
                  'category': 'object_actions',
                  },
                 {'id': 'useroptions',
                  'name': 'Wiki options',
                  'action': 'python:object.preferencesUrl()',
                  'permissions': (Permissions.View,),
                  'category': 'object_actions',
                  'visible': 0,
                  },
                 METADATA_TAB,
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
