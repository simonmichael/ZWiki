# -*- coding: utf-8 -*-
# provide generic i18n support

#problems.. due to circular import ?
#from Utils import BLATHER
#XXX temp
def BLATHER(t):
    import zLOG
    zLOG.LOG('ZWiki',zLOG.BLATHER,t)


USE_PTS=1

try:
    if USE_PTS:
        from Products.PlacelessTranslationService.MessageID import MessageIDFactory
        from Products.PlacelessTranslationService.PatchStringIO import get_request
        class MessageIDFactoryWithUtf8Fix(MessageIDFactory):
            """
            XXX hacky wrapper ensuring proper utf-8 negotiation when _ is used.

            Called for every i18n string, performance sensitive ?
            Disables itself during unit testing.  
            """
            def __call__(self, ustr, default=None):
                REQUEST = get_request()
                if REQUEST:
                    REQUEST.RESPONSE.setHeader( 
                        'Content-Type','text/html; charset=utf-8')
                return MessageIDFactory.__call__(self,ustr,default)
        _ = MessageIDFactoryWithUtf8Fix(
            'zwiki',
            # trying to make PTS return utf-8 translations so testI18n.py
            # can be utf8-encoded.. no effect
            default_encoding='utf-8')
        from Products.PageTemplates.PageTemplateFile import PageTemplateFile
        from Globals import HTMLFile, DTMLFile
        BLATHER('using PlacelessTranslationService for i18n')

    elif USE_LOCALIZER:
        from Products.Localizer import Gettext
        _ = Gettext.translation(globals())
        from Products.Localizer import LocalPageTemplateFile as PageTemplateFile
        from Products.Localizer import LocalDTMLFile as DTMLFile
        from DocumentTemplate.DT_String import String
        from DocumentTemplate.DT_Util import InstanceDict, namespace, render_blocks
        BLATHER('using Localizer for i18n - not implemented')

except (ImportError, NameError):
    def _(s): return s
    from Products.PageTemplates.PageTemplateFile import PageTemplateFile
    from Globals import HTMLFile, DTMLFile
    BLATHER('using no i18n')

