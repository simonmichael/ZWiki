# PAGE TYPES
# these objects encapsulate various kinds of
# parsing/formatting/rendering/processing behaviour for a particular
# zwiki page type.  I've long felt that these might want to be
# objects; let's extract methods from ZWikiPage and see what happens.
# Answer: the State pattern. It should be cleaner overall.
# These have no state themselves, they are pure behaviour, and we
# generally pass in the page context as first argument.
# They could be singleton objects, unless that has problems with persistence..
# XXX check ram cache manager code

from pagetypes.common import *

from pagetypes.stx import ZwikiStxPageType
from pagetypes.html import ZwikiHtmlPageType
from pagetypes.rst import ZwikiRstPageType
from pagetypes.wwml import ZwikiWwmlPageType
from pagetypes.plaintext import ZwikiPlaintextPageType

PAGETYPES = [
    ZwikiStxPageType,
    ZwikiRstPageType,
    ZwikiWwmlPageType,
    ZwikiHtmlPageType,
    ZwikiPlaintextPageType,
    ]

# a dictionary of ids and names used by legacy skin templates
PAGE_TYPES = {}
for t in PAGETYPES: PAGE_TYPES[t._id]=t._name
