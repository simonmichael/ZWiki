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
        _ = MessageIDFactoryWithUtf8Fix('zwiki')
        from Products.PageTemplates.PageTemplateFile import PageTemplateFile
        from Globals import HTMLFile, DTMLFile
        BLATHER('using PlacelessTranslationService for i18n')

    elif USE_LOCALIZER: # not supported at the moment
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
    class DummyTranslateTag:
        name='translate'
        blockContinuations=()
        _msgid = None
        _domain = None
        def __init__(self, blocks): 
            self.blocks=blocks
            tname, args, section = blocks[0]
            self.__name__="%s %s" % (tname, args)
        def render(self, md):
            r=[]
            for tname, args, section in self.blocks:
                __traceback_info__=tname
                r.append(section(None, md))
            if r:
                if len(r) > 1: r = "(%s)\n" % join(r,' ')
                else: r = r[0]
            else:
                r = ''
            return r + '\n'
        __call__=render
    from DocumentTemplate.DT_String import String
    String.commands['translate'] = DummyTranslateTag
    BLATHER('using no i18n')
