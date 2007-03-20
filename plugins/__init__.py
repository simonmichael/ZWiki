"""
The plugins package, containing plugins providing non-core functionality.

A Zwiki plugin is a module or package that extends Zwiki's functionality,
usually by providing a mixin for ZWikiPage, thereby adding extra features
to all wiki pages at startup.  A true plugin can (a) be removed without
any ill effects aside from disabling the feature it provides, and (b) be
provided by a separate product.

Page types are another kind of plugin, residing in their own pagetypes
package. It seems helpful to keep them separate for the moment.

Non-core features which used to be in the main ZWiki package are
gradually being moved here and pluginised. Some of them still have
hard-coded dependencies in other parts of the code, such as:

- dependencies in the Admin upgrade methods - resolved ?
- edit calls purple numbers when setting text
- some page types call purple numbers during rendering
- issue tracker access key and link in wikipage template
- tracker action in CMFInit fti
- tracker hotkey in showAccessKeys
- issue linking and link colouring in renderLink
- isIssue arg support in pages
- issue creation in mailin
- show_issueproperties=0 in pagetypes/common renderText
- issue properties form rendering in page types

"""

from Products.ZWiki.Utils import BLATHER, formattedTraceback

# a kludge to subclass a runtime list of classes, since we can't modify
# __bases__ of an extension class. ZWikiPage subclasses each of these
# slots. We could also subclass a class whose __bases__ we can modify,
# see http://zwiki.org/1034Pluginization
class Null: pass
PLUGINS = [
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    Null,
    ]

def registerPlugin(c):
    """
    Add a class to Zwiki's global plugin registry.

    >>> from Products.ZWiki.plugins import registerPlugin
    >>> registerPlugin(MyMixinClass)

    """
    name = '%s.%s' % (c.__module__,c.__name__)
    for i in range(len(PLUGINS)):
        if PLUGINS[i] == Null:
            PLUGINS[i] = c
            BLATHER('loaded plugin: %s' % name)
            return
    BLATHER('could not register %s plugin, need more plugin slots!' % name)

# load plugins
# import all modules and packages in this directory, each will register itself
import os, re
modules = [re.sub('.py$','',f) for f in os.listdir(__path__[0])
           if os.path.isdir(os.path.join(__path__[0], f))
           or (f.endswith('.py')
               and not f.endswith('_tests.py')
               and not f == '__init__.py'
               )
           ]
for m in modules:
    if m.startswith('_'):
        BLATHER('%s plugin disabled with _ prefix, skipping\n' % m[1:])
    else:
        try:
            __import__('Products.ZWiki.plugins.%s' % m)
        except ImportError:
            BLATHER('could not load %s plugin, skipping (traceback follows)\n%s' % (
                m, formattedTraceback()))
