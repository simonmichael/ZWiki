from types import *
import os, re, os.path
from string import join, split, strip

from AccessControl import getSecurityManager, ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from Products.ZWiki import Permissions
from Products.ZWiki.i18n import _
from Products.ZWiki.Utils import BLATHER, DEBUG, formattedTraceback
from Products.ZWiki.plugins import registerPlugin


class TinyMCESupport:
    """
    This mix-in class provides ZTinyMCE wysiwyg editor integration.
    """
    security = ClassSecurityInfo()

    security.declareProtected(Permissions.View, 'tinyMCEInstalled')
    def tinyMCEInstalled(self):
        """Is TinyMCE installed and configured?"""
        installed = 'ZTinyMCE' in self.Control_Panel.Products.objectIds()
        return installed and getattr(self, 'tinymce.conf', None) is not None

    security.declareProtected(Permissions.View, 'supportsTinyMCE')
    def supportsTinyMCE(self):
        """Is TinyMCE editing available for this page?"""
        return self.tinyMCEInstalled() and self.pageTypeId() == 'html'

    security.declareProtected(Permissions.AddWiki, 'setupTinyMCE')
    def setupTinyMCE(self):
        """
        Setup ZTinyMCE - if installed - with a useful config object.
        """
        if not 'ZTinyMCE' in self.Control_Panel.Products.objectIds():
            return 'ZTinyMCE is not installed.' # XXX proper page, localize
        folder = self.folder()
        if 'TinyMCE' not in folder.objectIds():
            folder.manage_addProduct['ZTinyMCE'].manage_addZTinyMCE( \
                'TinyMCE', 'WYSIWYG Editor Plugin')
        if 'tinymce.conf' not in folder.objectIds():
            conftext = """mode : "textareas",
theme : "advanced",
plugins : "table,advimage,advlink,emotions,contextmenu,paste,directionality,noneditable",
theme_advanced_buttons2_add : "forecolor,backcolor",
theme_advanced_buttons2_add_before: "cut,copy,paste,pastetext,pasteword,separator",
theme_advanced_buttons3_add_before : "tablecontrols,separator",
theme_advanced_buttons3_add : "emotions,separator,ltr,rtl,separator",
theme_advanced_toolbar_location : "top",
theme_advanced_toolbar_align : "left",
extended_valid_elements : "hr[class|width|size|noshade],font[face|size|color|style],span[class|align|style]" """
            folder.manage_addProduct['ZTinyMCE'].manage_addZTinyConfiguration(
                    'tinymce.conf', conftext, optimize=True,
                    title='TinyMCE in ZWiki config')

InitializeClass(TinyMCESupport)
registerPlugin(TinyMCESupport)
