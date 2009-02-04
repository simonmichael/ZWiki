from types import *
import os, re, os.path
from string import join, split, strip

from AccessControl import getSecurityManager, ClassSecurityInfo
from Globals import InitializeClass

from Products.ZWiki import Permissions
from Products.ZWiki.I18n import _
from Products.ZWiki.Utils import BLATHER, DEBUG, formattedTraceback, safe_hasattr
from Products.ZWiki.plugins import registerPlugin


class EpozSupport:
    """
    This mix-in class provides Epoz wysiwyg editor integration.
    """
    security = ClassSecurityInfo()

    security.declareProtected(Permissions.View, 'epozInstalled')
    def epozInstalled(self):
        """Is Epoz installed ?"""
        return 'Epoz' in self.Control_Panel.Products.objectIds()

    security.declareProtected(Permissions.View, 'supportsEpoz')
    def supportsEpoz(self):
        """Is Epoz editing available for this page ?"""
        return self.epozInstalled() and self.pageTypeId() == 'html'


InitializeClass(EpozSupport)
registerPlugin(EpozSupport)
