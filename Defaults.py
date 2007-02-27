######################################################################
# global flags and constants for ZWiki
# see also plugins/*

PAGE_METATYPE =      'ZWiki Page' # meta_type of ZWikiPage objects
PAGE_PORTALTYPE =    'Wiki Page'  # content type used in CMF/Plone
WIKI_ADD_MENU_NAME = 'ZWiki'      # items in ZMI add menu.. 
PAGE_ADD_MENU_NAME = 'ZWiki Page' # (this one must match PAGE_METATYPE)

AUTO_UPGRADE = 1             # upgrade old pages when viewed
DISABLE_JAVASCRIPT = 1       # disable javascript, etc. in edits ?
PREFER_USERNAME_COOKIE = 0   # prefer cookie to authenticated name ?
MAX_NEW_LINES_DISPLAY = 200  # truncate each diff (and mailout)
MAX_OLD_LINES_DISPLAY = 20   # at this number of lines
LINK_TO_ALL_CATALOGED = 0    # link to all pages in the catalog ? unimplemented
LINK_TO_ALL_OBJECTS = 0      # link to non-wiki page objects ? unimplemented
LARGE_FILE_SIZE = 1024*1024  # images larger than this will not be inlined
LEAVE_PLACEHOLDER = 0        # leave a placeholder page when renaming ?
WIKINAME_LINKS = 1           # enable/disable various wiki link syntaxes 
ISSUE_LINKS = 1              # by default
BRACKET_LINKS = 1
DOUBLE_BRACKET_LINKS = 1
DOUBLE_PARENTHESIS_LINKS = 0
BORING_PAGES = ['TestPage','SandBox'] # pages we don't want to see/hear much
IDS_TO_AVOID = ['RESPONSE','REQUEST','Epoz','epoz','URL','outline','recycle_bin']
CONDITIONAL_HTTP_GET = 0     # handle If-modified-since headers with 304 responses
CONDITIONAL_HTTP_GET_IGNORE = [ 'allow_dtml' ] 
                             # ignore pages with these properties set to 
                             # non-False values

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


# standard catalog indexes which should be present for best performance.
# setupCatalog will install these. Included here so they are easy to find.

TEXTINDEXES = [
    'Title',
    'text',
    ]
#XXX are these correct choice of FieldIndexes vs. KeywordIndexes ?
FIELDINDEXES = [
    'isBoring',
    'creation_time',
    'creator',
    'id',
    'last_edit_time',
    'last_editor',
    'meta_type',
    'page_type',
    'rating',
    'voteCount',
    ]
KEYWORDINDEXES = [
    'canonicalLinks',
    #'links', # XXX problems for epoz/plone, not needed ?
    'parents',
    ]
DATEINDEXES = [
    'creationTime',
    'lastEditTime',
    ]
PATHINDEXES = [
    'path',
    ]

