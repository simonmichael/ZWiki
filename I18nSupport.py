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


USE_PTS=1

try:
    if USE_PTS:
        from Products.PlacelessTranslationService import ZopeMessageIDFactory as _
        N_ = _

    elif USE_LOCALIZER:
        from Products.Localizer import Gettext
        _ = Gettext.translation(globals())
        N_ = Gettext.dummy
        from Products.Localizer import LocalDTMLFile, LocalPageTemplateFile

except (ImportError, NameError):
    # for Python code
    def _(s, language=None):
        return s
    N_ = _

    # For DTML and Page Templates
    def gettext(self, message, language=None):
        """ """
        return message

    # Document Template Markup Langyage (DTML)
    from Globals import DTMLFile

    class LocalDTMLFile(DTMLFile):
        def _exec(self, bound_data, args, kw):
            # Add our gettext first
            bound_data['gettext'] = self.gettext
            return apply(LocalDTMLFile.inheritedAttribute('_exec'),
                         (self, bound_data, args, kw))

        gettext = gettext

    # for Page Templates
    try:
        from Products.PageTemplates.PageTemplateFile import PageTemplateFile
    except ImportError:
        # If ZPT is not installed
        class LocalPageTemplateFile:
            pass
    else:
        class LocalPageTemplateFile(PageTemplateFile):
            def _exec(self, bound_data, args, kw):
                # Add our gettext first
                bound_data['gettext'] = self.gettext

                return apply(LocalPageTemplateFile.inheritedAttribute('_exec'),
                             (self, bound_data, args, kw))

            gettext = gettext

    # for DTML
    from DocumentTemplate.DT_Util import InstanceDict, namespace, render_blocks

    class GettextTag:
        """ """

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


    # Register the dtml-gettext tag
    from DocumentTemplate.DT_String import String
    if not String.commands.has_key('gettext'):
        String.commands['gettext'] = GettextTag
