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
registerPageType. Quick start:

- copy one of the existing modules (files) in this package; give your page
  type a suitable class name, _id and _name; register it at the end.
  Or: put your module in a separate zope product and call registerPageType
  in your __init__.py.

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

    >>> from Products.ZWiki.pagetypes import registerPageType
    >>> registerPageType(MyPageTypeClass)

    """
    if prepend: pos = 0
    else: pos = len(PAGETYPES)
    PAGETYPES.insert(pos,t)
    PAGE_TYPES[t._id] = t._name
    BLATHER('registered page type: %s (%s)'%(t._id,t._name))

def registerPageTypeUpgrade(old,new):
    """
    Add a page type transition to ZWiki's list of auto-upgrades.

    >>> from Products.ZWiki.pagetypes import registerPageTypeUpgrade
    >>> registerPageTypeUpgrade('oldpagetypeid','newpagetypeid')

    """
    PAGE_TYPE_UPGRADES[old] = new

# import all modules in this directory so that each will register its page type
import os,glob,re
modules = glob.glob(__path__[0] + os.sep + '*.py')
modules.remove(__path__[0] + os.sep + '__init__.py')
# force the usual ordering of standard page types in the editform
# FIXME this is not robust against new page types, or the removal of a page
# type.  Instead the ZWikiWeb install should add the folder property
# 'allowed_page_types' which specifies an order.
firstmods = ['stx.py','rst.py','wwml.py','html.py','plaintext.py']
firstmods.reverse()
for mod in firstmods:
    try:
        modules.remove(__path__[0] + os.sep + mod)
        modules.insert(0,__path__[0] + os.sep + mod)
    except ValueError:
        pass
for file in modules:
    m = re.search(r'%s([^%s]+?)\.py$'%(os.sep, os.sep), file)
    file = m.group(1)
    __import__('Products.ZWiki.pagetypes.%s' % file)

# XXX backwards compatibility
# keep the classes here for a bit to stop warnings
from plaintext import ZwikiPlaintextPageType
from html import ZwikiHtmlPageType
from stx import ZwikiStxPageType
from rst import ZwikiRstPageType
from wwml import ZwikiWwmlPageType

