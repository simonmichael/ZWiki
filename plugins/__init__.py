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

from Products.ZWiki.Utils import BLATHER

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
            BLATHER('registered plugin: %s' % name)
            return
    BLATHER('could not register plugin: %s, need more plugin slots!' % name)

# import all modules in this directory so that each will register its plugin
import os,glob,re
modules = glob.glob(__path__[0] + os.sep + '*.py')
modules.remove(__path__[0] + os.sep + '__init__.py')
for file in modules:
    m = re.search(r'%s([^%s]+?)\.py$'%(os.sep, os.sep), file)
    file = m.group(1)
    __import__('Products.ZWiki.plugins.%s' % file)
