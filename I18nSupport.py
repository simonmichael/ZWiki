# -*- coding: utf-8 -*-
# provide generic i18n support
#
# Localizer support copyright (C) 2002  Juan David IbáÂñez Palomar <j-david@noos.fr>

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.


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
        # XXX temp workaround
        from Products.PlacelessTranslationService.PatchStringIO import get_request
        class MessageIDFactoryWithUtf8Fix(MessageIDFactory):
            """
            A hacky wrapper to ensure utf-8 encoding whenever _ is used.
            """
            def __call__(self, ustr, default=None):
                try:
                    get_request().RESPONSE.setHeader(
                        'Content-Type','text/html; charset=utf-8')
                except AttributeError:
                    pass # for unit testing
                return MessageIDFactory.__call__(self,ustr,default)

        # python code
        # does not support language arg
        _ = gettext = MessageIDFactoryWithUtf8Fix('zwiki') 

        # page templates
        from Products.PageTemplates.PageTemplateFile import PageTemplateFile

        # DTML
        from Globals import DTMLFile as DTMLFileBase
        class DTMLFile(DTMLFileBase):
            def gettext(self, message, language=None): return _(message)
            def _exec(self, bound_data, args, kw):
                import pdb; pdb.set_trace()
                bound_data['gettext'] = self.gettext
                return apply(DTMLFileBase.inheritedAttribute('_exec'),
                             (self, bound_data, args, kw))
        
        BLATHER('using PlacelessTranslationService for i18n')

    elif USE_LOCALIZER:
        from Products.Localizer import Gettext
        _ = Gettext.translation(globals())
        from Products.Localizer import LocalPageTemplateFile as PageTemplateFile
        from Products.Localizer import LocalDTMLFile as DTMLFile

        BLATHER('using Localizer for i18n - not implemented')

except (ImportError, NameError):
    # python code
    def _(s, language=None): return s

    # page templates
    from Products.PageTemplates.PageTemplateFile import PageTemplateFile

    # DTML
    from Globals import DTMLFile as DTMLFileBase
    class DTMLFile(DTMLFileBase):
        # does not support language arg
        def gettext(self, message, language=None): return _(message)
        def _exec(self, bound_data, args, kw):
            bound_data['gettext'] = self.gettext
            return apply(DTMLFileBase.inheritedAttribute('_exec'),
                         (self, bound_data, args, kw))

    BLATHER('using no i18n')

# register the dtml-gettext tag.. ?
from DocumentTemplate.DT_String import String
if not String.commands.has_key('gettext'): 
    from DocumentTemplate.DT_Util import InstanceDict, namespace, render_blocks
    class GettextTag:
        name = 'gettext'
        blockContinuations = ()
        def __init__(self, blocks):
            tname, args, section = blocks[0]
            self.section = section.blocks
        def __call__(self, md):
            ns = namespace(md)[0]
            md._push(InstanceDict(ns, md))
            message = render_blocks(self.section, md)
            md._pop(1)
            return message
    String.commands['gettext'] = GettextTag    
