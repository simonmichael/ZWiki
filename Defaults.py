######################################################################
# global flags and constants for ZWiki
# see also plugins/*

DISABLE_JAVASCRIPT = 1       # disable javascript, etc. in edits ?
PREFER_USERNAME_COOKIE = 0   # prefer cookie to authenticated name ?
MAX_NEW_LINES_DISPLAY = 200  # truncate each diff (and mailout)
MAX_OLD_LINES_DISPLAY = 20   # at this number of lines
LINK_TO_ALL_CATALOGED = 0    # link to all pages in the catalog ? unimplemented
LINK_TO_ALL_OBJECTS = 0      # link to non-wiki page objects ? unimplemented
AUTO_UPGRADE = 1             # upgrade old pages when viewed
LARGE_FILE_SIZE = 1024*1024  # images larger than this will not be inlined
LEAVE_PLACEHOLDER = 0        # leave a placeholder page when renaming ?
SHOW_CURRENT_PAGE_IN_CONTENTS = 1 # scroll in contents (=> more robot urls)
DEFAULT_DISPLAYMODE = 'minimal'   # default display mode for the standard skin

PAGE_METATYPE =      'ZWiki Page' # meta_type of ZWikiPage objects
PAGE_PORTALTYPE =    'Wiki Page'  # content type used in CMF/Plone
WIKI_ADD_MENU_NAME = 'ZWiki'      # items in ZMI add menu.. 
PAGE_ADD_MENU_NAME = 'ZWiki Page' # (this one must match PAGE_METATYPE)


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
    #'links', # XXX problems for epoz/plone, not needed ?
    'page_type',     
    'parents',
    'rating',
    'severity',
    'severity_index',
    'size',
    'status',
    'status_index',
    'subscriber_list',
    'summary',
    'voteCount',
    ]

IDS_TO_AVOID = ['RESPONSE','REQUEST','Epoz','epoz']
