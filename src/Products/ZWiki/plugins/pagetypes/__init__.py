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
  overrideable page-type-specific methods in common.PageTypeBase.
  Don't forget to modify your supports* methods as appropriate.

"""

from Products.ZWiki.Utils import INFO, BLATHER, formattedTraceback
from types import StringType

# global page type registry
#XXX print "__init__.py: setting PAGETYPES to []"
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
    'Classic Wiki'                 :'plaintext',
    'Plain Text'                   :'plaintext',
    # pre-0.9.10
    'stxprelinkdtml'               :'stx',
    'structuredtextdtml'           :'stx',
    'dtmlstructuredtext'           :'stx',
    'structuredtext'               :'stx',
    'structuredtextonly'           :'stx',
    'classicwiki'                  :'plaintext',
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
    'wwmllink'                     :'plaintext',
    'wwmlprelink'                  :'plaintext',
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
    'wwmlprelinkfitissue'          :'plaintext',
    # pre-0.22
    'msgstxprelinkfitissuehtml'    :'stx',
    # nb pre-.22 'html' pages will not be auto-upgraded
    #'html'                         :'html',
    # pre-0.32
    'msgstxprelinkdtmlfitissuehtml':'stx',
    'msgrstprelinkfitissue'        :'rst',
    'msgwwmlprelinkfitissue'       :'plaintext',
    'dtmlhtml'                     :'html',
    # pre-2.0
#     'wwml'                         :'plaintext',
#     'moin'                         :'plaintext',
#     'stxlatex'                     :'plaintext',
#     'stxmath'                      :'plaintext',
#     'pamphlet'                     :'plaintext',
    }

def registerPageType(t,prepend=0):
    """
    Add a page type class to Zwiki's global registry, optionally at the front.

    >>> from Products.ZWiki.plugins.pagetypes import registerPageType
    >>> registerPageType(MyPageTypeClass)

    """
    if prepend: pos = 0
    else: pos = len(PAGETYPES)
    PAGETYPES.insert(pos,t)
    PAGE_TYPES[t._id] = t._name
    BLATHER('loaded page type: %s (%s)'%(t._id,t._name))

def registerPageTypeUpgrade(old,new):
    """
    Add a page type transition to ZWiki's list of auto-upgrades.

    >>> from Products.ZWiki.plugins.pagetypes import registerPageTypeUpgrade
    >>> registerPageTypeUpgrade('oldpagetypeid','newpagetypeid')

    """
    PAGE_TYPE_UPGRADES[old] = new

# import pagetype modules/packages in this directory, each will register itself
import os, re
modules = [re.sub('.py$','',f) for f in os.listdir(__path__[0])
           if os.path.isdir(os.path.join(__path__[0], f))
           or (f.endswith('.py')
               and not f.endswith('_tests.py')
               and not f == '__init__.py'
               )
           ]
# enforce the order of at least the first few page types in the editform
# can be overridden with the 'allowed_page_types' folder property
firstmods = ['rst','stx','html','plaintext']
firstmods.reverse()
for mod in firstmods:
    try:
        modules.remove(mod)
        modules.insert(0, mod)
    except ValueError:
        pass
# and import
for m in modules:
    if m.startswith('_'):
        INFO('%s page type disabled with _ prefix, skipping\n' % m[1:])
    else:
        try:
            __import__('Products.ZWiki.plugins.pagetypes.%s' % m)
        except (ImportError, ValueError):
            INFO('could not load %s page type, skipping (traceback follows)\n%s' % (
                m, formattedTraceback()))

# backwards compatibility - old zwiki page objects expect these to be here

# but if a page type has been disabled with a _ prefix, just ignore
# XXX can't really disable yet, these get imported somewhere else
#def tryImport(module, fromlist):
#    try: __import__(module,globals(),locals(),fromlist)
#    except ImportError: pass

try:
    import html
    ZwikiHtmlPageType = html.PageTypeHtml
except ImportError:
    pass
try:
    import plaintext
    ZwikiPlaintextPageType = plaintext.PageTypePlaintext
except ImportError:
    pass
try:
    import rst
    ZwikiRstPageType = rst.PageTypeRst
except ImportError:
    pass
try:
    import stx
    ZwikiStxPageType = stx.PageTypeStx
except ImportError:
    pass

def defaultPageType():
    """The default page type object, from all the known page types."""
    return PAGETYPES[0]

def pageTypeWithId(id):
    """Return the page type object corresponding to this page type id, or
    the default page type."""
    for t in PAGETYPES:
        if t._id == id: return t
    return defaultPageType()

def modernPageTypeFor(t):
    """Find the best modern equivalent for some arbitrary old page type,
    which could be a string or a (possibly broken) page type object.

    This may be confusing. Know that Zwiki versions 0.25-2.0 kept a
    *PageType instance in the page_type property; older and later versions
    keep an id string there.
    """
    if type(t) != StringType:
        return pageTypeWithId(t.getId())._id
    else:
        return PAGE_TYPE_UPGRADES.get(t, defaultPageType()._id)

