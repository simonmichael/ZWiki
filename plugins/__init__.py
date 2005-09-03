# experimental package for non-core plugin modules
#
# A Zwiki plugin is a module (file) providing a mixin class that extends
# ZWikiPage, thereby adding extra features to all wiki pages at startup.
# A true plugin (a) can be removed without ill effect aside from disabling
# the feature it provides, and (b) could be provided by a separate
# product.
# 
# Mixins which used to be in the main ZWiki package are gradually being
# moved here and pluginised. Some of them still have dependencies in other
# parts of the code, eg
#
# - Editing calls purple numbers when setting text
# 
# - some page types call purple numbers during rendering
#
# - dependencies in the standard and plone skins - what do we do here ?
#
# page types are another kind of "plugin", residing in their own pagetypes
# package. 

from Products.ZWiki.Utils import BLATHER, formattedTraceback

# a nasty way to subclass a runtime list of classes, since we can't modify
# __bases__ of an extension class - ZWikiPage.ZWikiPage must subclass each
# of these slots explicitly
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
            #BLATHER('registered %s plugin' % name)
            return
    BLATHER('could not register %s plugin, need more plugin slots!' % name)

# load plugins
# import all modules and packages in this directory, each will register itself
import os, re
BLATHER('loading plugins:')
plugins = [re.sub('.py$','',p) for p in os.listdir(__path__[0])
           if not p.endswith('.pyc') 
           and not p in ('__init__.py','README')]
for p in plugins:
    try:
        __import__('Products.ZWiki.plugins.%s' % p)
        BLATHER('loaded %s plugin' % p)
    except:
        BLATHER('could not load %s plugin, skipping (traceback follows)\n%s' % (
            p, formattedTraceback()))
