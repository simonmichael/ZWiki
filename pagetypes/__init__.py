# PAGE TYPES
"""
A zwiki page holds a page type object (in its page_type attribute) to
which it delegates certain methods, so that formatting and other behaviour
can be changed by replacing this page type object with another (the State
pattern). Page type objects hold no state aside from their class, so when
calling them we usually pass in the page as first argument.
XXX cf ram cache manager code to check for persistence issue ?

To define a new page type, add a module in this package or in a separate
zope product which subclasses any of the *PageType classes, and call
registerPageType at startup. Quick start:

- copy one of the existing modules (files) in this package; give your page
  type a suitable class name, _id and _name; register it with the others
  at the end of this file.  Or: put your module in a separate zope product
  and call registerPageType in your __init__.py.

- restart zope or refresh zwiki; your page type should appear in the editform

- tweak your page type until it does what you want. You can see a list of
  overrideable page-type-specific methods in common.AbstractPageType.
  Don't forget to modify your supports* methods as appropriate.

"""

from Products.ZWiki.Utils import BLATHER

# global page type registry
PAGETYPES = []

# ids-to-names mapping used by legacy skin templates
PAGE_TYPES = {}

# legacy page types to auto-upgrade
PAGE_TYPE_UPGRADES = {
    # early zwiki
    'Structured Text'              :'stx',
    'structuredtext_dtml'          :'stx',
    'HTML'                         :'html',
    'html_dtml'                    :'html',
    'Classic Wiki'                 :'wwml',
    'Plain Text'                   :'plaintext',
    # pre-0.9.10
    'stxprelinkdtml'               :'stx',
    'structuredtextdtml'           :'stx',
    'dtmlstructuredtext'           :'stx',
    'structuredtext'               :'stx',
    'structuredtextonly'           :'stx',
    'classicwiki'                  :'wwml',
    'htmldtml'                     :'html',
    'plainhtmldtml'                :'html',
    'plainhtml'                    :'html',
    # pre-0.17
    'stxprelinkdtmlhtml'           :'stx',
    'issuedtml'                    :'stx',
    # pre-0.19
    'stxdtmllinkhtml'              :'stx',
    'dtmlstxlinkhtml'              :'stx',
    'stxprelinkhtml'               :'stx',
    'stxlinkhtml'                  :'stx',
    'stxlink'                      :'stx',
    'wwmllink'                     :'wwml',
    'wwmlprelink'                  :'wwml',
    'prelinkdtmlhtml'              :'html',
    'dtmllinkhtml'                 :'html',
    'prelinkhtml'                  :'html',
    'linkhtml'                     :'html',
    'textlink'                     :'plaintext',
    # pre-0.20
    'stxprelinkfitissue'           :'stx',
    'stxprelinkfitissuehtml'       :'stx',
    'stxprelinkdtmlfitissuehtml'   :'stx',
    'rstprelinkfitissue'           :'rst',
    'wwmlprelinkfitissue'          :'wwml',
    # pre-0.22
    'msgstxprelinkfitissuehtml'    :'stx',
    # nb pre-.22 'html' pages will not be auto-upgraded
    #'html'                         :'html',
    # pre-0.32
    'msgstxprelinkdtmlfitissuehtml':'stx',
    'msgrstprelinkfitissue'        :'rst',
    'msgwwmlprelinkfitissue'       :'wwml',
    'dtmlhtml'                     :'html',
    }

def registerPageType(t,prepend=0):
    """
    Add a page type class to Zwiki's global registry, optionally at the front.

    Example: registerPageType(MyPageTypeClass)
    """
    if prepend: pos = 0
    else: pos = len(PAGETYPES)
    PAGETYPES.insert(pos,t)
    PAGE_TYPES[t._id] = t._name
    BLATHER('registered page type: %s (%s)'%(t._id,t._name))

def registerPageTypeUpgrade(old,new):
    """
    Add a page type transition to ZWiki's list of auto-upgrades.

    Example: registerPageTypeUpgrade('oldpagetypeid','newpagetypeid')
    """
    PAGE_TYPE_UPGRADES[old] = new

from common import MIDSECTIONMARKER
from plaintext import ZwikiPlaintextPageType
from html import ZwikiHtmlPageType
from stx import ZwikiStxPageType
from rst import ZwikiRstPageType
from wwml import ZwikiWwmlPageType

# the order these are registered in is the order they will appear
# in the editform by default, and the first is the default type
for t in [
    ZwikiStxPageType,
    ZwikiRstPageType,
    ZwikiWwmlPageType,
    ZwikiHtmlPageType,
    ZwikiPlaintextPageType,
    ]: registerPageType(t)
