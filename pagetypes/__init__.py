# PAGE TYPES
"""

Zwiki page type objects are singleton State objects which encapsulate any
behaviour which is specific to the different kinds of zwiki page. They
hold no state of their own so we usually pass in the page object as first
argument.  XXX cf ram cache manager code to check for persistence issues

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

def registerPageType(t,prepend=0):
    """
    Add a page type class to Zwiki's global registry, optionally at the front.
    """
    if prepend: pos = 0
    else: pos = len(PAGETYPES)
    PAGETYPES.insert(pos,t)
    PAGE_TYPES[t._id] = t._name

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
