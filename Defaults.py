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

IDS_TO_AVOID = ['RESPONSE','REQUEST','Epoz','epoz','URL','outline','recycle_bin']

# Standard metadata fields which Zwiki will expect in page brain objects.
# Plugins will add more of these.
# NB for best large-wiki performance, all of these must be in the wiki
# catalog so that ensureCompleteMetadataIn() does not have to go to the
# ZODB. To be safe, setupCatalog will add them all.
# see also http://zwiki.org/ZwikiAndZCatalog
PAGE_METADATA = [
    'Title',
    'creation_time',
    'creator',      
    'id',
    'lastEditTime',
    'last_edit_time',
    'last_editor',   
    'last_log',
    'page_type',     
    'parents',
    'size',
    'subscriber_list',
    'summary',
    #'links', # XXX problems for epoz/plone, not needed ?
    ]

#from Utils import BLATHER
def registerPageMetaData(t):
    """
    Add an attribute name to the list of standard page metadata.

    >>> from Products.ZWiki.Defaults import registerPageMetaData
    >>> registerPageMetaData('myattribute')

    """
    PAGE_METADATA.append(t)
    #BLATHER('registered standard metadata field: %s'%t)

