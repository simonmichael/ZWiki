# PAGE TYPES
"""
Zwiki page type objects are State objects which encapsulate any behaviour
which is specific to the different kinds of zwiki page. All pages hold an
instance of the appropriate page type class in their page_type attribute.
XXX cf ram cache manager code to check for persistence issues ?
Page type objects hold no state of their own so when calling them we
usually pass in the page object as first argument.

You can plug in new zwiki page types by adding a new page type module in this
package, or in a separate zope product, and calling registerPageType at
startup. Your page type can inherit from one of the abstract page types in
common.py, or any other page type. All overrideable page-type-specific
methods appear in common.AbstractPageType.

Quick start:

- copy one of the existing modules in this package
- give the class a suitable name, _id and _name
- register it below
- restart or refresh zwiki; it should appear in the editform
- tweak it until it does what you want
- don't forget to modify your supports* methods too

"""

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

for t in [
    ZwikiStxPageType,
    ZwikiRstPageType,
    ZwikiWwmlPageType,
    ZwikiHtmlPageType,
    ZwikiPlaintextPageType,
    ]: registerPageType(t)
