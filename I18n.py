# -*- coding: utf-8 -*-
# provide generic i18n support

import re

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
        # an i18n doc claimed it's good for _ to return a MessageIDFactory for
        # some unicode reason, but it causes problems here and there for
        # code that expects a string. We'll convert to a string for now.
        # Also we'll put an ugly try except to allow this to just work
        # in unit tests. Performance problem ?
        #_ = lambda s:str(MessageIDFactory('zwiki')(s))
        def _(s):
            try:
                return str(MessageIDFactory('zwiki')(s))
            except AttributeError:
                return str(s)
        # this hack forced proper utf-8 header with PTS, but I seem not to
        # need it any more.. possibly since zope 2.7.2 or some other upgrade ?
        # reenable if utf-8 encoding is broken, and please report at zwiki.org
        # XXX still happening with "you are here" in wiki contents view ?
        #class MessageIDFactoryWithUtf8Fix(MessageIDFactory):
        #    """
        #    XXX wrapper ensuring proper utf-8 http header when _ is used.
        #
        #    Called for every i18n string, performance sensitive ?
        #    When there is no request, do nothing so unit tests can run.
        #    """
        #    def __call__(self, ustr, default=None):
        #        def setResponseCharset(RESPONSE, charset):
        #            contenttype = RESPONSE.getHeader('content-type') or 'text/html'
        #            if not 'charset' in contenttype:
        #                RESPONSE.setHeader('Content-Type','%s; charset=utf-8' % contenttype)
        #        REQUEST = get_request()
        #        if not REQUEST: return ustr
        #        else:
        #            setResponseCharset(REQUEST.RESPONSE,'utf-8')
        #            return MessageIDFactory.__call__(self,ustr,default)
        #_ = lambda s:str(MessageIDFactoryWithUtf8Fix('zwiki')(s))
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
    class MockTranslateTag:
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
    String.commands['translate'] = MockTranslateTag
    BLATHER('did not find PlacelessTranslationService, the Zwiki skin will not be localized')
