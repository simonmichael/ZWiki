# -*- coding: utf-8 -*-
# provide generic i18n support

#problems.. due to circular import ?
#from Utils import BLATHER
#XXX temp
def BLATHER(t):
    import zLOG
    zLOG.LOG('ZWiki',zLOG.BLATHER,t)

import re

USE_PTS=1

try:
    if USE_PTS:
        from Products.PlacelessTranslationService.MessageID import MessageIDFactory
        from Products.PlacelessTranslationService.PatchStringIO import get_request
        class MessageIDFactoryWithUtf8Fix(MessageIDFactory):
            """
            XXX hacky wrapper ensuring proper utf-8 http header when _ is used.

            Called for every i18n string, performance sensitive ?

            When there is no request, does nothing to allow unit tests to
            run.

            Also: an i18n doc I've seen (find ref) thinks that _()
            returning a MessageIDFactory rather than a string is a good
            thing for some unicode reason, but it causes problems here and
            there for code that expects a string. We'll convert to a
            string for now.
            """
            def __call__(self, ustr, default=None):
                REQUEST = get_request()
                if REQUEST:
                    mycontent = REQUEST.RESPONSE.getHeader('content-type')
                    if mycontent == None:
                        mycontent = 'text/html'
                    if not re.search(r'charset', mycontent):
                        REQUEST.RESPONSE.setHeader( 
                            'Content-Type',  mycontent + '; charset=utf-8')
                    return MessageIDFactory.__call__(self,ustr,default)
                else:
                    return ustr
        _ = lambda s:str(MessageIDFactoryWithUtf8Fix('zwiki')(s))
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
