# experimental package for non-core plugin modules
#
# A Zwiki plugin is a module providing a mixin class that extends
# ZWikiPage, thereby adding extra features to all wiki pages at startup.
# A true plugin (a) can be removed without ill effect aside from disabling
# the feature it provides, and (b) could be provided by a separate
# product.
# 
# Mixins which used to be in the main ZWiki package are gradually being
# moved here and pluginised (some of them still have hard-coded
# dependencies in other parts of the code).
#
# page types are another kind of add-on, residing in their own pagetypes
# package. We may invent others.

#def registerPlugin(p): pass

#from PurpleNumbers import PurpleNumbersSupport

#for p in [
#    PurpleNumbersSupport,
#    ]: registerPlugin(t)
