######################################################################
# global flags and constants for ZWiki

DISABLE_JAVASCRIPT = 1       # disable javascript, etc. in edits ?
PREFER_USERNAME_COOKIE = 0   # prefer cookie to authenticated name ?
MAX_NEW_LINES_DISPLAY = 200  # truncate each diff (and mailout)
MAX_OLD_LINES_DISPLAY = 20   # at this number of lines
LINK_TO_ALL_CATALOGED = 0    # link to all pages in the catalog ? unimplemented
LINK_TO_ALL_OBJECTS = 0      # link to non-wiki page objects ? unimplemented
AUTO_UPGRADE = 1             # upgrade old pages when viewed
LARGE_FILE_SIZE = 1024*1024  # images larger than this will not be inlined
LEAVE_PLACEHOLDER = 0        # leave a placeholder page when renaming ?
SCROLL_CONTENTS = 0          # scroll to current page in contents (=>many urls)

PAGE_METATYPE =      'ZWiki Page' # meta_type of ZWikiPage objects
PAGE_PORTALTYPE =    'Wiki Page'  # content type used in CMF/Plone
WIKI_ADD_MENU_NAME = 'ZWiki'      # items in ZMI add menu.. 
PAGE_ADD_MENU_NAME = 'ZWiki Page' # (this one must match PAGE_METATYPE)

# the page types we'll offer in the default edit form,
# unless overridden by an allowed_page_types property.
# These must match the ids in PageTypes.py.
ALLOWED_PAGE_TYPES = [
    'msgstxprelinkdtmlfitissuehtml',
    'msgrstprelinkfitissue',
    'msgwwmlprelinkfitissue',
    'dtmlhtml',
    'plaintext',
    ]
# ditto for wikis in CMF/Plone
ALLOWED_PAGE_TYPES_IN_PLONE = [
    'msgstxprelinkdtmlfitissuehtml',
    'msgrstprelinkfitissue',
    #'msgwwmlprelinkfitissue',
    'dtmlhtml',
    'plaintext',
    ]

# issue tracker defaults, will be installed as folder properties
ISSUE_CATEGORIES = [
    'general',
    ]
ISSUE_SEVERITIES = [
    'critical',
    'serious',
    'normal',
    'minor',
    'wishlist',
    ]
ISSUE_STATUSES = [
    'open',
    'pending',
    'closed',
    ]
# this is a list of strings like 'category,status,severity,colour' any of
# which may be empty (a wildcard). The first entry matching the issue
# will be used.
ISSUE_COLOURS = [
    ',open,critical ,#ff2222',
    ',open,serious  ,#ff6060',
    ',open,normal   ,#ffbbbb',
    ',open,minor    ,#ffdddd',
    ',open,wishlist ,#e0e0e0',
    ',open,         ,#ffe0e0',
    ',pending,      ,#ffcc77',
    ',closed,       ,#e0f0e0',
    ',,             ,',
    ]

# standard metadata fields Zwiki expects to be in page brain objects
# for best large-wiki performance, ensure these are in catalog metadata
# (all of them! since pages() will otherwise go to the ZODB to get them)
# see also http://zwiki.org/ZwikiAndZCatalog
PAGE_METADATA = [
    'Title',
    #'cachedSize',
    'category',
    'category_index',
    'creation_time',
    'creator',      
    'id',
    'issueColour',
    'lastEditTime',
    'last_edit_time',
    'last_editor',   
    'last_log',
    'links',
    'page_type',     
    'parents',
    'severity',
    'severity_index',
    'size',
    'status',
    'status_index',
    'subscriber_list',
    'summary',
    ]

# for reStructuredText:
# You can customize the default encoding by creating a file
# sitecustomize.py somewhere in yout PYTHONPATH:
#  import sys
#  sys.setdefaultencoding("iso-8859-1")
#import sys
#sys.setdefaultencoding("iso-8859-1")
#hmm not right
