# experimental package for non-core plugin modules
#
# A Zwiki plugin is a module providing a mixin class that extends
# ZWikiPage, thereby adding extra features to all wiki pages.  Like page
# types, it should be possible for zwiki plugins to be provided by other
# products also.
#
# Mixins which used to be in the main ZWiki package are gradually being
# moved here. Some of them may still have hard-coded dependencies in other
# parts of the code. Code has been completely plugin-ized if: you can
# remove it without ill effect other than disabling the feature and if it
# could be provided by another product.

#def registerPlugin(p): pass

#from PurpleNumbers import PurpleNumbersSupport

#for p in [
#    PurpleNumbersSupport,
#    ]: registerPlugin(t)
