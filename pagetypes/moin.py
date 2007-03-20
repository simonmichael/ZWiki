# -*- coding: iso-8859-1 -*-
"""
A MoinMoin page type for Zwiki, supporting most of MoinMoin 1.3b2's markup.
This can make migration between Moin and Zwiki easier.
Thanks to Canonical for providing a bounty for this feature.

Copyrights:

MoinMoin Wiki Markup Parser and "text/html+css" Formatter,
copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
license: GNU GPL, see COPYING for details.

Modified by Simon Michael for Zwiki moin markup support.
Copyright 2004-2005 Simon Michael for the Zwiki community 

This is all in one file for convenience of the plugin handling code.  It
is moin 1.3b2's parsers/wiki.py and formatter/text_html.py with wiki
linking and troublesome bits (macros) hacked out, Moin prefix added to a
few classes, plus the usual Zwiki page type class.
"""

import os, re, string
from common import *
from Products.ZWiki.I18n import _
from Products.ZWiki.pagetypes import registerPageType

class PageTypeMoin(PageTypeBase):
    _id = 'moin'
    _name = 'MoinMoin'
    supportsMoin = yes
    supportsWikiLinks = yes

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+\
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.format(t)
        t = page.markLinksIn(t)
        t = self.protectEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        if page.hasFitTests(): t = page.runFitTestsIn(t)
        if page.isIssue() and kw.get('show_issueproperties',1):
            t = page.addIssueFormTo(t)
        t = page.renderMidsectionIn(t,**kw)
        t = page.addSkinTo(t,**kw)
        return t

    def format(self,t):
        # moin assumes utf-8 everwhere, like zwiki (except where we can't,
        # see moin_support)
        return render_moin_markup(unicode(t,'utf-8')).encode('utf-8')


######################################################################
# modified moin 1.3b2 parsing/formatting code

# character encoding issues
#
# - moin hard-codes utf-8 everywhere like zwiki, but we need the system's
# actual configured encoding to encode string.uppercase etc. below 
# (cf http://zwiki.org/963)
#
# - similar to Regexps.py don't rely on python 2.3's getpreferredencoding, 
# which gives wrong answer (?)
# and work around a python bug with some locales (http://zwiki.org/392).
# 
# - XXX problems remain with some locales, see http://zwiki.org/809

import locale
try:
    encoding = locale.getlocale()[1] or 'utf-8'
except ValueError:
    encoding = 'utf-8'


class MoinConfig:
    pass

class MoinRequest:
    output = u''
    form = None
    getText = None
    cfg = MoinConfig()
    _page_headings = {}
    def write(self, text): self.output += text
    def __unicode__(self): return self.output
    def getPragma(self,a,b): return b

class MoinParser:
    """
        Object that turns Wiki markup into HTML.

        All formatting commands can be parsed one line at a time, though
        some state is carried over between lines.

        Methods named like _*_repl() are responsible to handle the named regex
        patterns defined in print_html().
    """

    # allow caching
    caching = 1

    # some common strings
    PARENT_PREFIX = '' #wikiutil.PARENT_PREFIX
    attachment_schemas = ["attachment", "inline", "drawing"]
    punct_pattern = re.escape(u'''"\'}]|:,.)?!''')
    #url_pattern = (u'http|https|ftp|nntp|news|mailto|telnet|wiki|file|' +
    url_pattern = (u'http|https|ftp|nntp|news|mailto|telnet|file')
            #u'|'.join(attachment_schemas) + 
            #(config.url_schemas and u'|' + u'|'.join(config.url_schemas) or ''))

    # some common rules
    word_rule = ur'(?:(?<![%(l)s])|^)%(parent)s(?:%(subpages)s(?:[%(u)s][%(l)s]+){2,})+(?![%(u)s%(l)s]+)' % {
        'u': unicode(string.uppercase,encoding),
        'l': unicode(string.lowercase,encoding),
        'subpages':'', #config.allow_subpages and (wikiutil.CHILD_PREFIX + '?') or '',
        'parent':'', #config.allow_subpages and (ur'(?:%s)?' % re.escape(PARENT_PREFIX)) or '',
    }
    url_rule = ur'%(url_guard)s(%(url)s)\:([^\s\<%(punct)s]|([%(punct)s][^\s\<%(punct)s]))+' % {
        'url_guard': u'(^|(?<!\w))',
        'url': url_pattern,
        'punct': punct_pattern,
    }

    ol_rule = ur"^\s+(?:[0-9]+|[aAiI])\.(?:#\d+)?\s"
    dl_rule = ur"^\s+.*?::\s"

    # the big, fat, ugly one ;)
    formatting_rules = ur"""(?:(?P<emph_ibb>'''''(?=[^']+'''))
(?P<emph_ibi>'''''(?=[^']+''))
(?P<emph_ib_or_bi>'{5}(?=[^']))
(?P<emph>'{2,3})
(?P<u>__)
(?P<sup>\^.*?\^)
(?P<sub>,,[^,]{1,40},,)
(?P<tt>\{\{\{.*?\}\}\})
(?P<processor>(\{\{\{(#!.*|\s*$)))
(?P<pre>(\{\{\{ ?|\}\}\}))
(?P<small>(\~- ?|-\~))
(?P<big>(\~\+ ?|\+\~))
(?P<rule>-{4,})
(?P<comment>^\#\#.*$)
(?P<macro>\[\[(%%(macronames)s)(?:\(.*?\))?\]\]))
(?P<ol>%(ol_rule)s)
(?P<dl>%(dl_rule)s)
(?P<li>^\s+\*?)
(?P<tableZ>\|\| $)
(?P<table>(?:\|\|)+(?:<[^>]*?>)?(?!\|? $))
(?P<heading>^\s*(?P<hmarker>=+)\s.*\s(?P=hmarker) $)
(?P<word>%(word_rule)s)
(?P<url_bracket>\[((%(url)s)\:|#|\:)[^\s\]]+(\s[^\]]+)?\])
(?P<url>%(url_rule)s)
(?P<email>[-\w._+]+\@[\w-]+(\.[\w-]+)+)
(?P<ent>[<>&])"""  % {
        'url': url_pattern,
        'punct': punct_pattern,
        'ol_rule': ol_rule,
        'dl_rule': dl_rule,
        'url_rule': url_rule,
        'word_rule': word_rule,
        'smiley': u'|'.join(map(re.escape, []))} #config.smileys.keys()))}
#(?P<smiley>(?<=\s)(%(smiley)s)(?=\s))
#(?P<smileyA>^(%(smiley)s)(?=\s))
#(?P<interwiki>[A-Z][a-zA-Z]+\:[^\s'\"\:\<\|]([^\s%(punct)s]|([%(punct)s][^\s%(punct)s]))+)

    no_new_p_before = ["heading", "rule", "table", "tableZ", "tr", "td",
                       "ul", "ol", "dl", "dt", "dd", "li"]

    def __init__(self, raw, request, **kw):
        self.raw = raw
        self.request = request
        self.form = request.form
        self._ = request.getText
        self.cfg = request.cfg

        self.macro = None

        self.is_em = 0
        self.is_b = 0
        self.is_u = 0
        self.lineno = 0
        self.in_li = 0
        self.in_dd = 0
        self.in_pre = 0
        self.in_table = 0
        self.is_big = False
        self.is_small = False
        self.inhibit_p = 0 # if set, do not auto-create a <p>aragraph
        self.titles = request._page_headings

        # holds the nesting level (in chars) of open lists
        self.list_indents = []
        self.list_types = []
        
        #self.formatting_rules = self.formatting_rules % {'macronames': u'|'.join(wikimacro.getNames(self.cfg))}

    def _close_item(self, result):
        #result.append("<!-- close item begin -->\n")
        if self.in_table:
            result.append(self.formatter.table(0))
            self.in_table = 0
        if self.in_li:
            self.in_li = 0
            if self.formatter.in_p:
                result.append(self.formatter.paragraph(0))
            result.append(self.formatter.listitem(0))
        if self.in_dd:
            self.in_dd = 0
            if self.formatter.in_p:
                result.append(self.formatter.paragraph(0))
            result.append(self.formatter.definition_desc(0))
        #result.append("<!-- close item end -->\n")


    def interwiki(self, url_and_text, **kw):
        # TODO: maybe support [wiki:Page http://wherever/image.png] ?
        if len(url_and_text) == 1:
            url = url_and_text[0]
            text = None
        else:
            url, text = url_and_text

        url = url[5:] # remove "wiki:"
        if text is None:
            tag, tail = wikiutil.split_wiki(url)
            if tag:
                text = tail
            else:
                text = url
                url = ""
        elif 0: #config.allow_subpages and url[0] == wikiutil.CHILD_PREFIX:
            # fancy link to subpage [wiki:/SubPage text]
            return self._word_repl(url, text)
        elif 0: #Page(self.request, url).exists():
            # fancy link to local page [wiki:LocalPage text]
            return self._word_repl(url, text)

        wikitag, wikiurl, wikitail, wikitag_bad = wikiutil.resolve_wiki(self.request, url)
        href = wikiutil.join_wiki(wikiurl, wikitail)

        # check for image URL, and possibly return IMG tag
        if not kw.get('pretty_url', 0) and wikiutil.isPicture(wikitail):
            return self.formatter.image(src=href)

        # link to self?
        if wikitag is None:
            return self._word_repl(wikitail)
              
        return (self.formatter.interwikilink(1, wikitag, wikitail) + 
                self.formatter.text(text) +
                self.formatter.interwikilink(0))

    def attachment(self, url_and_text, **kw):
        """ This gets called on attachment URLs.
        """
        import urllib
        _ = self._
        if len(url_and_text) == 1:
            url = url_and_text[0]
            text = None
        else:
            url, text = url_and_text

        inline = url[0] == 'i'
        drawing = url[0] == 'd'
        url = url.split(":", 1)[1]
        url = urllib.unquote(url)
        text = text or url

        pagename = self.formatter.page.page_name
        parts = url.split('/')
        if len(parts) > 1:
            # get attachment from other page
            pagename = '/'.join(parts[:-1])
            url = parts[-1]

        import urllib
        from MoinMoin.action import AttachFile
        fname = wikiutil.taintfilename(url)
        if drawing:
            drawing = fname
            fname = fname + ".png"
            url = url + ".png"
            # fallback for old gif drawings (1.1 -> 1.2)
            fpath = os.path.join(AttachFile.getAttachDir(self.request, pagename), fname)
            if not os.path.exists(fpath):
                gfname = fname[:-4] + ".gif"
                gurl = url[:-4] + ".gif"
                gfpath = os.path.join(AttachFile.getAttachDir(self.request, pagename), gfname)
                if os.path.exists(gfpath):
                    fname, url, fpath = gfname, gurl, gfpath
        else:
            fpath = os.path.join(AttachFile.getAttachDir(self.request, pagename), fname)

        # check whether attachment exists, possibly point to upload form
        if not os.path.exists(fpath):
            if drawing:
                linktext = _('Create new drawing "%(filename)s"')
            else:
                linktext = _('Upload new attachment "%(filename)s"')
            return wikiutil.link_tag(self.request,
                '%s?action=AttachFile&amp;rename=%s%s' % (
                    wikiutil.quoteWikinameURL(pagename),
                    urllib.quote_plus(fname.encode(config.charset)),
                    drawing and ('&amp;drawing=%s' % urllib.quote(drawing.encode(config.charset))) or ''),
                linktext % {'filename': fname})

        # check for image URL, and possibly return IMG tag
        # (images are always inlined, just like for other URLs)
        if not kw.get('pretty_url', 0) and wikiutil.isPicture(url):
            if drawing:
                # check for map file
                mappath = os.path.join(AttachFile.getAttachDir(self.request, pagename), drawing + '.map')
                edit_link = '%s?action=AttachFile&amp;rename=%s&amp;drawing=%s' % (wikiutil.quoteWikinameURL(pagename), urllib.quote_plus(fname.encode(config.charset)), urllib.quote(drawing.encode(config.charset)))
                if os.path.exists(mappath):
                    # we have a image map. inline it and add a map ref
                    # to the img tag
                    try:
                        map = open(mappath,'r').read()
                    except IOError:
                        pass
                    except OSError:
                        pass
                    else:
                        mapid = 'ImageMapOf'+drawing
                        # replace MAPNAME
                        map = map.replace('%MAPNAME%', mapid)
                        # add alt and title tags to areas
                        map = re.sub('href\s*=\s*"((?!%TWIKIDRAW%).+?)"',r'href="\1" alt="\1" title="\1"',map)
                        # add in edit links plus alt and title attributes
                        map = map.replace('%TWIKIDRAW%"', edit_link + '" alt="' + _('Edit drawing %(filename)s') % {'filename': fname} + '" title="' + _('Edit drawing %(filename)s') % {'filename': fname} + '"')
                        # unxml, because 4.01 concrete will not validate />
                        map = map.replace('/>','>')
                        return map + self.formatter.image(alt=drawing,
                                src=AttachFile.getAttachUrl(pagename, url, self.request, addts=1), usemap='#'+mapid, html_class="drawing")
                else:
                    return wikiutil.link_tag(self.request,
                        edit_link,
                        self.formatter.image(alt=url,
                            src=AttachFile.getAttachUrl(pagename, url, self.request, addts=1), html_class="drawing"),
                        attrs='title="%s"' % (_('Edit drawing %(filename)s') % {'filename': fname}))
            else:
                return self.formatter.image(alt=url,
                    src=AttachFile.getAttachUrl(pagename, url, self.request, addts=1))

        # try to inline the attachment (parser know what they
        # can handle)
        base, ext = os.path.splitext(url)
        if inline:
            Parser = wikiutil.getParserForExtension(self.cfg, ext)
            if Parser is not None:
                colorizer = MoinParser(open(fpath, 'r').read(), self.request)
                colorizer.format(self.formatter)

        url = AttachFile.getAttachUrl(pagename, url, self.request)

        if kw.get('pretty_url', 0) and wikiutil.isPicture(url):
            return self.formatter.image(src=url)
        else:
            return (self.formatter.url(1, url) +
                    self.formatter.text(text) +
                    self.formatter.url(0))

    def _u_repl(self, word):
        """Handle underline."""
        self.is_u = not self.is_u
        return self.formatter.underline(self.is_u)

    def _small_repl(self, word):
        """Handle small."""
        if word.strip() == '~-' and self.is_small: return word
        if word.strip() == '-~' and not self.is_small: return word
        self.is_small = not self.is_small
        return self.formatter.small(self.is_small)

    def _big_repl(self, word):
        """Handle big."""
        if word.strip() == '~+' and self.is_big: return word
        if word.strip() == '+~' and not self.is_big: return word
        self.is_big = not self.is_big
        return self.formatter.big(self.is_big)

    def _emph_repl(self, word):
        """Handle emphasis, i.e. '' and '''."""
        ##print "#", self.is_b, self.is_em, "#"
        if len(word) == 3:
            self.is_b = not self.is_b
            if self.is_em and self.is_b: self.is_b = 2
            return self.formatter.strong(self.is_b)
        else:
            self.is_em = not self.is_em
            if self.is_em and self.is_b: self.is_em = 2
            return self.formatter.emphasis(self.is_em)

    def _emph_ibb_repl(self, word):
        """Handle mixed emphasis, i.e. ''''' followed by '''."""
        self.is_b = not self.is_b
        self.is_em = not self.is_em
        if self.is_em and self.is_b: self.is_b = 2
        return self.formatter.emphasis(self.is_em) + self.formatter.strong(self.is_b)

    def _emph_ibi_repl(self, word):
        """Handle mixed emphasis, i.e. ''''' followed by ''."""
        self.is_b = not self.is_b
        self.is_em = not self.is_em
        if self.is_em and self.is_b: self.is_em = 2
        return self.formatter.strong(self.is_b) + self.formatter.emphasis(self.is_em)

    def _emph_ib_or_bi_repl(self, word):
        """Handle mixed emphasis, exactly five '''''."""
        ##print "*", self.is_b, self.is_em, "*"
        b_before_em = self.is_b > self.is_em > 0
        self.is_b = not self.is_b
        self.is_em = not self.is_em
        if b_before_em:
            return self.formatter.strong(self.is_b) + self.formatter.emphasis(self.is_em)
        else:
            return self.formatter.emphasis(self.is_em) + self.formatter.strong(self.is_b)


    def _sup_repl(self, word):
        """Handle superscript."""
        return self.formatter.sup(1) + \
            self.formatter.text(word[1:-1]) + \
            self.formatter.sup(0)


    def _sub_repl(self, word):
        """Handle subscript."""
        return self.formatter.sub(1) + \
            self.formatter.text(word[2:-2]) + \
            self.formatter.sub(0)


    def _rule_repl(self, word):
        """Handle sequences of dashes."""
        self.inhibit_p = 1
        result = self._undent()
        if len(word) <= 4:
            result = result + self.formatter.rule()
        else:
            result = result + self.formatter.rule(min(len(word), 10) - 2)
        return result


    def _word_repl(self, word, text=None):
        """Handle WikiNames."""

        # check for parent links
        # !!! should use wikiutil.AbsPageName here, but setting `text`
        # correctly prevents us from doing this for now
        if 0: #config.allow_subpages and word.startswith(self.PARENT_PREFIX):
            if not text: text = word
            word = '/'.join(filter(None, self.formatter.page.page_name.split('/')[:-1] + [word[3:]]))

        if not text:
            # if a simple, self-referencing link, emit it as plain text
            if word == self.formatter.page.page_name:
                return self.formatter.text(word)
            text = word
        if 0: #config.allow_subpages and word.startswith(wikiutil.CHILD_PREFIX):
            word = self.formatter.page.page_name + word
        return (#self.formatter.pagelink(1, word) +
                self.formatter.text(text))# +
                #self.formatter.pagelink(0))

    def _notword_repl(self, word):
        """Handle !NotWikiNames."""
        return self.formatter.text(word[1:])


    def _interwiki_repl(self, word):
        """Handle InterWiki links."""
        return self.interwiki(["wiki:" + word])


    def _url_repl(self, word):
        """Handle literal URLs including inline images."""
        scheme = word.split(":", 1)[0]

        #if scheme == "wiki": return self.interwiki([word])
        if scheme in self.attachment_schemas:
            return self.attachment([word])

        if wikiutil.isPicture(word):
            return self.formatter.image(src=word)
        else:
            return (self.formatter.url(1, word, type='www') +
                    self.formatter.text(word) +
                    self.formatter.url(0))


    def _wikiname_bracket_repl(self, word):
        """Handle special-char wikinames."""
        wikiname = word[2:-2]
        if wikiname:
            return self._word_repl(wikiname)
        else:
            return word


    def _url_bracket_repl(self, word):
        """Handle bracketed URLs."""

        # Local extended link?
        if word[1] == ':':
            words = word[2:-1].split(':', 1)
            if len(words) == 1: words = words * 2
            return self._word_repl(words[0], words[1])

        # Traditional split on space
        words = word[1:-1].split(None, 1)
        if len(words) == 1: words = words * 2

        if words[0][0] == '#':
            # anchor link
            return (self.formatter.url(1, words[0]) +
                    self.formatter.text(words[1]) +
                    self.formatter.url(0))

        scheme = words[0].split(":", 1)[0]
        #if scheme == "wiki": return self.interwiki(words, pretty_url=1)
        if scheme in self.attachment_schemas:
            return self.attachment(words, pretty_url=1)

        if wikiutil.isPicture(words[1]) and re.match(self.url_rule, words[1]):
            return (self.formatter.url(1, words[0], 'external', unescaped=1) +
                    self.formatter.image(title=words[0], alt=words[0], src=words[1]) +
                    self.formatter.url(0))
        else:
            return (self.formatter.url(1, words[0], 'external',
                                       type='www', unescaped=1) +
                    self.formatter.text(words[1]) +
                    self.formatter.url(0))


    def _email_repl(self, word):
        """Handle email addresses (without a leading mailto:)."""
        return (self.formatter.url(1, "mailto:" + word, type='mailto') +
                self.formatter.text(word) +
                self.formatter.url(0))


    def _ent_repl(self, word):
        """Handle SGML entities."""
        return self.formatter.text(word)
        #return {'&': '&amp;',
        #        '<': '&lt;',
        #        '>': '&gt;'}[word]


    def _ent_numeric_repl(self, word):
        """Handle numeric SGML entities."""
        return self.formatter.rawHTML(word)


    def _li_repl(self, match):
        """Handle bullet lists."""
        result = []
        indented_only = (match == (" " * len(match)))
        if indented_only and self.in_li: return ''
            
        self._close_item(result)
        #self.inhibit_p = 1
        self.in_li = 1
        css_class = ''
        if self.line_was_empty and not self.first_list_item:
            css_class = 'gap'
        if indented_only:
            result.append(self.formatter.listitem(1, css_class=css_class,
                                             style="list-style-type:none"))
        else:
            result.append(self.formatter.listitem(1, css_class=css_class))
        result.append(self.formatter.paragraph(1))
        return ''.join(result)


    def _ol_repl(self, match):
        """Handle numbered lists."""
        return self._li_repl(match)


    def _dl_repl(self, match):
        """Handle definition lists."""
        result = []
        self._close_item(result)
        #self.inhibit_p = 1
        self.in_dd = 1
        result.extend([
            self.formatter.definition_term(1),
            self.formatter.text(match[:-3]),
            self.formatter.definition_term(0),
            self.formatter.definition_desc(1),
            self.formatter.paragraph(1)
        ])
        return ''.join(result)


    def _indent_level(self):
        """Return current char-wise indent level."""
        return len(self.list_indents) and self.list_indents[-1]


    def _indent_to(self, new_level, list_type, numtype, numstart):
        """Close and open lists."""
        open = []   # don't make one out of these two statements!
        close = []


        if self._indent_level() != new_level and self.in_table:
            close.append(self.formatter.table(0))
            self.in_table = 0
        #    #self._close_item(close)
        #else:
        #    if not self.line_was_empty:
        #        self.inhibit_p = 1
    
        # Close lists while char-wise indent is greater than the current one
        while ((self._indent_level() > new_level) or
               ( new_level and
                (self._indent_level() == new_level) and
                (self.list_types[-1]) != list_type)):
            self._close_item(close)
            if self.list_types[-1] == 'ol':
                tag = self.formatter.number_list(0)
            elif self.list_types[-1] == 'dl':
                tag = self.formatter.definition_list(0)
            else:
                tag = self.formatter.bullet_list(0)
            close.append(tag)

            del(self.list_indents[-1])
            del(self.list_types[-1])
            
            #if new_level:
            #    self.inhibit_p = 1
            #else:
            #    self.inhibit_p = 0

            if self.list_types: # we are still in a list
                if self.list_types[-1] == 'dl':
                    self.in_dd = 1
                else:
                    self.in_li = 1
                
        # Open new list, if necessary
        if self._indent_level() < new_level:
                    
            self.list_indents.append(new_level)
            self.list_types.append(list_type)

            if self.formatter.in_p:
                close.append(self.formatter.paragraph(0))
            
            if list_type == 'ol':
                tag = self.formatter.number_list(1, numtype, numstart)
            elif list_type == 'dl':
                tag = self.formatter.definition_list(1)
            else:
                tag = self.formatter.bullet_list(1)
            open.append(tag)
            
            self.first_list_item = 1
            self.inhibit_p = 1
            self.in_li = 0
            self.in_dd = 0
        # If list level changes, close an open table
        if self.in_table and (open or close):
            close[0:0] = [self.formatter.table(0)]
            self.in_table = 0

        self.inhibit_p = bool(self.list_types)

        return ''.join(close) + ''.join(open)


    def _undent(self):
        """Close all open lists."""
        result = []
        #result.append("<!-- _undent start -->\n")
        self._close_item(result)
        for type in self.list_types:
            if type == 'ol':
                result.append(self.formatter.number_list(0))
            elif type == 'dl':
                result.append(self.formatter.definition_list(0))
            else:
                result.append(self.formatter.bullet_list(0))
        #result.append("<!-- _undent end -->\n")
        self.list_indents = []
        self.list_types = []
        return ''.join(result)


    def _tt_repl(self, word):
        """Handle inline code."""
        return self.formatter.code(1) + \
            self.formatter.text(word[3:-3]) + \
            self.formatter.code(0)


    def _tt_bt_repl(self, word):
        """Handle backticked inline code."""
        if len(word) == 2: return ""
        return self.formatter.code(1) + \
            self.formatter.text(word[1:-1]) + \
            self.formatter.code(0)


    def _getTableAttrs(self, attrdef):
        # skip "|" and initial "<"
        while attrdef and attrdef[0] == "|":
            attrdef = attrdef[1:]
        if not attrdef or attrdef[0] != "<":
            return {}, ''
        attrdef = attrdef[1:]

        # extension for special table markup
        def table_extension(key, parser, attrs, wiki_parser=self):
            _ = wiki_parser._
            msg = ''
            if key[0] in "0123456789":
                token = parser.get_token()
                if token != '%':
                    wanted = '%'
                    msg = _('Expected "%(wanted)s" after "%(key)s", got "%(token)s"') % {
                        'wanted': wanted, 'key': key, 'token': token}
                else:
                    try:
                        dummy = int(key)
                    except ValueError:
                        msg = _('Expected an integer "%(key)s" before "%(token)s"') % {
                            'key': key, 'token': token}
                    else:
                        attrs['width'] = '"%s%%"' % key
            elif key == '-':
                arg = parser.get_token()
                try:
                    dummy = int(arg)
                except ValueError:
                    msg = _('Expected an integer "%(arg)s" after "%(key)s"') % {
                        'arg': arg, 'key': key}
                else:
                    attrs['colspan'] = '"%s"' % arg
            elif key == '|':
                arg = parser.get_token()
                try:
                    dummy = int(arg)
                except ValueError:
                    msg = _('Expected an integer "%(arg)s" after "%(key)s"') % {
                        'arg': arg, 'key': key}
                else:
                    attrs['rowspan'] = '"%s"' % arg
            elif key == '(':
                attrs['align'] = '"left"'
            elif key == ':':
                attrs['align'] = '"center"'
            elif key == ')':
                attrs['align'] = '"right"'
            elif key == '^':
                attrs['valign'] = '"top"'
            elif key == 'v':
                attrs['valign'] = '"bottom"'
            elif key == '#':
                arg = parser.get_token()
                try:
                    if len(arg) != 6: raise ValueError
                    dummy = int(arg, 16)
                except ValueError:
                    msg = _('Expected a color value "%(arg)s" after "%(key)s"') % {
                        'arg': arg, 'key': key}
                else:
                    attrs['bgcolor'] = '"#%s"' % arg
            else:
                msg = None
            #print "key: %s\nattrs: %s" % (key, str(attrs))
            return msg

        # scan attributes
        attr, msg = wikiutil.parseAttributes(self.request, attrdef, '>', table_extension)
        if msg: msg = '<strong class="highlight">%s</strong>' % msg
        #print attr
        return attr, msg

    def _tableZ_repl(self, word):
        """Handle table row end."""
        if self.in_table:
            result = ''
            if self.formatter.in_p and not self.in_li:
                result = self.formatter.paragraph(0)
            result += self.formatter.table_cell(0) + self.formatter.table_row(0)
            return result
        else:
            return word

    def _table_repl(self, word):
        """Handle table cell separator."""
        if self.in_table:
            # check for attributes
            attrs, attrerr = self._getTableAttrs(word)

            # start the table row?
            if self.table_rowstart:
                self.table_rowstart = 0
                leader = self.formatter.table_row(1, attrs)
            else:
                if self.formatter.in_p and not self.in_li:
                    leader = self.formatter.paragraph(0)
                else: leader = ''
                leader += self.formatter.table_cell(0)

            # check for adjacent cell markers
            if word.count("|") > 2:
                if not attrs.has_key('align'):
                    attrs['align'] = '"center"'
                if not attrs.has_key('colspan'):
                    attrs['colspan'] = '"%d"' % (word.count("|")/2)

            # return the complete cell markup           
            return leader + self.formatter.table_cell(1, attrs) + attrerr
        else:
            return word


    def _heading_repl(self, word):
        """Handle section headings."""
        import sha

        self.inhibit_p = 1
        icons = ''

        h = word.strip()
        level = 1
        while h[level:level+1] == '=':
            level = level+1
        depth = min(5,level)

        # this is needed for Included pages
        # TODO but it might still result in unpredictable results
        # when included the same page multiple times
        title_text = h[level:-level].strip()
        pntt = self.formatter.page.page_name + title_text
        self.titles.setdefault(pntt, 0)
        self.titles[pntt] += 1

        unique_id = ''
        if self.titles[pntt] > 1:
            unique_id = '-%d' % self.titles[pntt]

        result = self.formatter.heading(1, depth, id="head-"+sha.new(pntt.encode('utf-8')).hexdigest()+unique_id) #config.charset
                                     
        return (result + self.formatter.text(title_text) +
                self.formatter.heading(0, depth))
    
    def _processor_repl(self, word):
        """Handle processed code displays."""
        if word[:3] == '{{{': word = word[3:]

        self.processor = None
        self.processor_name = None
        self.processor_is_parser = 0
        s_word = word.strip()
        if s_word == '#!':
            # empty bang paths lead to a normal code display
            # can be used to escape real, non-empty bang paths
            word = ''
            self.in_pre = 3
            return  self.formatter.preformatted(1)
        elif 0: #s_word[:2] == '#!':
            # first try to find a processor for this (will go away in 1.4)
            processor_name = s_word[2:].split()[0]
            self.processor = wikiutil.importPlugin("processor", 
                                                   processor_name, 
                                                   "process", 
                                                   self.request.cfg.data_dir)
            # now look for a parser with that name
            if self.processor is None:
                self.processor = wikiutil.importPlugin("parser",
                                                       processor_name,
                                                       "Parser",
                                                       self.request.cfg.data_dir)
                if self.processor:
                    self.processor_is_parser = 1

        if self.processor:
            self.processor_name = processor_name
            self.in_pre = 2
            self.colorize_lines = [word]
            return ''
        elif s_word:
            self.in_pre = 3
            return self.formatter.preformatted(1) + \
                   self.formatter.text(s_word + ' (-)')
        else:
            self.in_pre = 1
            return ''

    def _pre_repl(self, word):
        """Handle code displays."""
        word = word.strip()
        if word == '{{{' and not self.in_pre:
            self.in_pre = 3
            self.inhibit_p = 1
            return self.formatter.preformatted(self.in_pre)
        elif word == '}}}' and self.in_pre:
            self.in_pre = 0
            self.inhibit_p = 0
            return self.formatter.preformatted(self.in_pre)
        return word


    def _smiley_repl(self, word):
        """Handle smileys."""
        return self.formatter.smiley(word)

    _smileyA_repl = _smiley_repl


    def _comment_repl(self, word):
        return ''


    def _macro_repl(self, word):
        """Handle macros ([[macroname]])."""
        macro_name = word[2:-2]
        #self.inhibit_p = 1 # fixes UserPreferences, but makes new trouble!

        # check for arguments
        args = None
        if macro_name.count("("):
            macro_name, args = macro_name.split('(', 1)
            args = args[:-1]

        # create macro instance
        if self.macro is None:
            self.macro = wikimacro.Macro(self)

        # call the macro
        return self.formatter.macro(self.macro, macro_name, args)

    def scan(self, scan_re, line):
        """ scans the line for wiki syntax and replaces the
            found regular expressions
        """
        result = []
        lastpos = 0
        match = scan_re.search(line)
        while match and lastpos < len(line):
            # add the match we found
            if lastpos<match.start():
                if not (self.inhibit_p or self.in_pre or
                        self.formatter.in_p):
                    result.append(self.formatter.paragraph(1))
                result.append(self.formatter.text(line[lastpos:match.start()]))
            result.append(self.replace(match))

            # search for the next one
            lastpos = match.end() + (match.end() == lastpos)
            match = scan_re.search(line, lastpos)


        if not (self.inhibit_p or self.in_pre or
                self.formatter.in_p) and lastpos<len(line):
            result.append(self.formatter.paragraph(1))
        result.append(self.formatter.text(line[lastpos:]))
        return u''.join(result)

    def replace(self, match):
        #hit = filter(lambda g: g[1], match.groupdict().items())
        for type, hit in match.groupdict().items():
            if hit is not None and type != "hmarker":
                ##print "###", cgi.escape(`type`), cgi.escape(`hit`), "###"
                if self.in_pre and type not in ['pre', 'ent']:
                    return hit
                else:
                    p = ''
                    if not (self.inhibit_p or self.formatter.in_p
                            or self.in_pre
                            or (type in self.no_new_p_before)):
                        p = self.formatter.paragraph(1)
                    return p + getattr(self, '_' + type + '_repl')(hit) 
        else:
            import pprint
            raise Exception("Can't handle match " + `match`
                + "\n" + pprint.pformat(match.groupdict())
                + "\n" + pprint.pformat(match.groups()) )

        return ""


    def format(self, formatter):
        """ For each line, scan through looking for magic
            strings, outputting verbatim any intervening text.
        """
        self.formatter = formatter
        #self.hilite_re = self.formatter.page.hilite_re

        # prepare regex patterns
        rules = self.formatting_rules.replace('\n', '|')
        if 1: #self.cfg.allow_extended_names:
            rules = rules + ur'|(?P<wikiname_bracket>\[".*?"\])'
        if 1: #self.cfg.bang_meta:
            rules = ur'(?P<notword>!%(word_rule)s)|%(rules)s' % {
                'word_rule': self.word_rule,
                'rules': rules,
            }
        if 1: #self.cfg.backtick_meta:
           rules = rules + ur'|(?P<tt_bt>`.*?`)'
        if 1: #self.cfg.allow_numeric_entities:
            rules = ur'(?P<ent_numeric>&#\d{1,5};)|' + rules

        scan_re = re.compile(rules, re.UNICODE)
        number_re = re.compile(self.ol_rule, re.UNICODE)
        term_re = re.compile(self.dl_rule, re.UNICODE)
        indent_re = re.compile("^\s*", re.UNICODE)
        eol_re = re.compile(r'\r?\n', re.UNICODE)

        # get text and replace TABs
        rawtext = self.raw.expandtabs()

        # go through the lines
        self.lineno = 0
        self.lines = eol_re.split(rawtext)
        self.line_is_empty = 0

        for line in self.lines:
            self.lineno = self.lineno + 1
            self.table_rowstart = 1
            self.line_was_empty = self.line_is_empty
            self.line_is_empty = 0
            self.first_list_item = 0
            self.inhibit_p = 0

            if self.in_pre:
                # still looking for processing instructions
                if self.in_pre == 1:
                    self.processor = None
                    self.processor_is_parser = 0
                    processor_name = ''
                    if 0: #(line.strip()[:2] == "#!"):
                        processor_name = line.strip()[2:].split()[0]
                        self.processor = wikiutil.importPlugin("processor",
                                                               processor_name,
                                                               "process",
                                                               self.request.cfg.data_dir)
                        # now look for a parser with that name
                        if self.processor is None:
                            self.processor = wikiutil.importPlugin("parser",
                                                                   processor_name,
                                                                   "Parser",
                                                                   self.request.cfg.data_dir)
                            if self.processor:
                                self.processor_is_parser = 1
                    if self.processor:
                        self.in_pre = 2
                        self.colorize_lines = [line]
                        self.processor_name = processor_name
                        continue
                    else:
                        self.request.write(self.formatter.preformatted(1))
                        self.in_pre = 3
                if self.in_pre == 2:
                    # processing mode
                    endpos = line.find("}}}")
                    if endpos == -1:
                        self.colorize_lines.append(line)
                        continue
                    if line[:endpos]:
                        self.colorize_lines.append(line[:endpos])
                    self.request.write(
                        self.formatter.processor(self.processor_name, self.colorize_lines, self.processor_is_parser))
                    del self.colorize_lines
                    self.in_pre = 0
                    self.processor = None

                    # send rest of line through regex machinery
                    line = line[endpos+3:]                    
            else:
                line = line + " " # we don't have \n as whitespace any more
                # paragraph break on empty lines
                if not line.strip():
                    #self.request.write("<!-- empty line start -->\n")
                    if self.in_table:
                        self.request.write(self.formatter.table(0))
                        self.in_table = 0
                    if (self.formatter.in_p and not self.list_types):
                        self.request.write(self.formatter.paragraph(0))
                    self.line_is_empty = 1
                    #self.request.write("<!-- empty line end -->\n")
                    continue

                # check indent level
                indent = indent_re.match(line)
                indlen = len(indent.group(0))
                indtype = "ul"
                numtype = None
                numstart = None
                if indlen:
                    match = number_re.match(line)
                    if match:
                        numtype, numstart = match.group(0).strip().split('.')
                        numtype = numtype[0]

                        if numstart and numstart[0] == "#":
                            numstart = int(numstart[1:])
                        else:
                            numstart = None

                        indtype = "ol"
                    else:
                        match = term_re.match(line)
                        if match:
                            indtype = "dl"

                # output proper indentation tags
                #self.request.write("<!-- inhibit_p==%d -->\n" % self.inhibit_p)
                #self.request.write("<!-- #%d calling _indent_to -->\n" % self.lineno)
                self.request.write(self._indent_to(indlen, indtype, numtype, numstart))
                #self.request.write("<!-- #%d after calling _indent_to -->\n" % self.lineno)
                #self.request.write("<!-- inhibit_p==%d -->\n" % self.inhibit_p)

                # start or end table mode
                if (not self.in_table and line[indlen:indlen+2] == "||"
                    and line[-3:] == "|| " and len(line)>=5+indlen):
                    if self.list_types and not self.in_li:
                        self.request.write(self.formatter.listitem
                                           (1, style="list-style-type:none"))
                        self.request.write(self.formatter.paragraph(1))
                        self.in_li = 1
                    if self.formatter.in_p and not self.in_li:
                        self.request.write(self.formatter.paragraph(0))
                    attrs, attrerr = self._getTableAttrs(line[indlen+2:])
                    self.request.write(self.formatter.table(1, attrs) + attrerr)
                    self.in_table = True # self.lineno
                elif self.in_table and not(line[:2]=="##" or # intra-table comments should not break a table 
                    line[indlen:indlen+2] == "||" and line[-3:] == "|| " and
                    len(line)>=5+indlen):
                    self.request.write(self.formatter.table(0))
                    self.in_table = 0
            # convert line from wiki markup to HTML and print it
            formatted_line = self.scan(scan_re, line)
            
            #self.request.write("<!-- %s\n     start -->\n" % line)
            self.request.write(formatted_line)
            #self.request.write("<!-- end -->\n")

            if self.in_pre:
                self.request.write(self.formatter.linebreak())

        # close code displays, paragraphs, tables and open lists
        if self.is_b: self.request.write(self.formatter.strong(0))
        if self.is_em: self.request.write(self.formatter.emphasis(0))
        if self.is_u: self.request.write(self.formatter.underline(0))
        
        self.request.write(self._undent())
        if self.in_pre: self.request.write(self.formatter.preformatted(0))
        if self.formatter.in_p: self.request.write(self.formatter.paragraph(0))
        if self.in_table: self.request.write(self.formatter.table(0))



class MoinFormatterBase:
    """ This defines the output interface used all over the rest of the code.

        Note that no other means should be used to generate _content_ output,
        while navigational elements (HTML page header/footer) and the like
        can be printed directly without violating output abstraction.
    """

    hardspace = ' '

    def __init__(self, request, **kw):
        self.request = request
        self._ = request.getText

        self._store_pagelinks = kw.get('store_pagelinks', 0)
        self._terse = kw.get('terse', 0)
        self.pagelinks = []
        self.in_p = 0
        self.in_pre = 0
        self._highlight_re = None
        self._base_depth = 0

    def set_highlight_re(self, hi_re=None):
        if type(hi_re) in [types.StringType, types.UnicodeType]:
            try:
                self._highlight_re = re.compile(hi_re, re.U + re.IGNORECASE)
            except re.error:
                hi_re = re.escape(hi_re)
                self._highlight_re = re.compile(hi_re, re.U + re.IGNORECASE)
        else:
            self._highlight_re = hi_re

    def lang(self, on, lang_name):
        return ""

    def setPage(self, page):
        self.page = page

    def sysmsg(self, on, **kw):
        """ Emit a system message (embed it into the page).

            Normally used to indicate disabled options, or invalid markup.
        """
        return ""

    # Document Level #####################################################
    
    def startDocument(self, pagename):
        return ""

    def endDocument(self):
        return ""

    def startContent(self, content_id="content", **kwargs):
        return ""

    def endContent(self):
        return ""

    def startContent(self, cid, extra=''):
        return ""

    def endContent(self):
        return ""

    # Links ##############################################################
    
    def pagelink(self, on, pagename='', **kw):
        if kw.get('generated', 0) or not on: return
        if self._store_pagelinks and pagename not in self.pagelinks:
            self.pagelinks.append(pagename)

    def interwikilink(self, on, interwiki='', pagename='', **kw):
        return ''
            

    def url(self, on, url=None, css=None, **kw):
        raise NotImplementedError

    def anchordef(self, name):
        return ""

    def anchorlink(self, on, name='', id=None):
        return ""

    def image(self, **kw):
        """ Take HTML <IMG> tag attributes in `attr`.

            Attribute names have to be lowercase!
        """
        attrstr = u''
        for attr, value in kw.items():
            if attr=='html_class':
                attr='class'
            attrstr = attrstr + u' %s="%s"' % (attr, wikiutil.escape(value))
        return u'<img%s>' % attrstr

    # Text and Text Attributes ########################################### 
    
    def text(self, text):
        if not self._highlight_re:
            return self._text(text)
            
        result = []
        lastpos = 0
        match = self._highlight_re.search(text)
        while match and lastpos < len(text):
            # add the match we found
            result.append(self._text(text[lastpos:match.start()]))
            result.append(self.highlight(1))
            result.append(self._text(match.group(0)))
            result.append(self.highlight(0))

            # search for the next one
            lastpos = match.end() + (match.end() == lastpos)
            match = self._highlight_re.search(text, lastpos)

        result.append(self._text(text[lastpos:]))
        return ''.join(result)

    def _text(self, text):
        raise NotImplementedError

    def strong(self, on):
        raise NotImplementedError

    def emphasis(self, on):
        raise NotImplementedError

    def underline(self, on):
        raise NotImplementedError

    def highlight(self, on):
        raise NotImplementedError

    def sup(self, on):
        raise NotImplementedError

    def sub(self, on):
        raise NotImplementedError

    def code(self, on):
        raise NotImplementedError

    def preformatted(self, on):
        self.in_pre = on != 0

    def small(self, on):
        raise NotImplementedError

    def big(self, on):
        raise NotImplementedError

    # special markup for syntax highlighting #############################

    def code_area(self, on, code_id, **kwargs):
        raise NotImplementedError

    def code_line(self, on):
        raise NotImplementedError

    def code_token(self, on, tok_type):
        raise NotImplementedError

    # special markup for syntax highlighting #############################

    def code_area(self, on, code_id, **kwargs):
        raise NotImplementedError

    def code_line(self, on):
        raise NotImplementedError

    def code_token(self, tok_text, tok_type):
        raise NotImplementedError

    # Paragraphs, Lines, Rules ###########################################

    def linebreak(self, preformatted=1):
        raise NotImplementedError

    def paragraph(self, on):
        self.in_p = on != 0

    def rule(self, size=0):
        raise NotImplementedError

    def icon(self, type):
        return type

    # Lists ##############################################################

    def number_list(self, on, type=None, start=None):
        raise NotImplementedError

    def bullet_list(self, on):
        raise NotImplementedError

    def listitem(self, on, **kw):
        raise NotImplementedError

    def definition_list(self, on):
        raise NotImplementedError

    def definition_term(self, on, compact=0):
        raise NotImplementedError

    def definition_desc(self, on):
        raise NotImplementedError

    def heading(self, on, depth, **kw):
        raise NotImplementedError

    # Tables #############################################################
    
    def table(self, on, attrs={}):
        raise NotImplementedError

    def table_row(self, on, attrs={}):
        raise NotImplementedError

    def table_cell(self, on, attrs={}):
        raise NotImplementedError

    # Dynamic stuff / Plugins ############################################
    
    def macro(self, macro_obj, name, args):
        # call the macro
        return macro_obj.execute(name, args)    

    def _split_hashbang(self, line):
        if line[:2]=='#!':
            name, args = line[2:].split(' ', 1)
            return args
        return None

    def processor(self, processor_name, lines, is_parser = 0):
        """ processor_name MUST be valid!
            writes out the result instead of returning it!
        """
        if not is_parser:
            processor = wikiutil.importPlugin("processor",
                                              processor_name, "process",
                                              self.request.cfg.data_dir)
            processor(self.request, self, lines)
        else:
            parser = wikiutil.importPlugin("parser",
                                           processor_name, "Parser",
                                           self.request.cfg.data_dir)
            args = self._split_hashbang(lines[0])
            if args is not None:
                lines = lines[1:]
            p = parser('\n'.join(lines), self.request, format_args = args)
            p.format(self)
            del p
        return ''

    def dynamic_content(self, parser, callback, arg_list = [], arg_dict = {},
                        returns_content = 1):
        content = parser[callback](*arg_list, **arg_dict)
        if returns_content:
            return content
        else:
            return ''

    # Other ##############################################################
    
    def rawHTML(self, markup):
        """ This allows emitting pre-formatted HTML markup, and should be
            used wisely (i.e. very seldom).

            Using this event while generating content results in unwanted
            effects, like loss of markup or insertion of CDATA sections
            when output goes to XML formats.
        """
        return markup

    def escapedText(self, on):
        """ This allows emitting text as-is, anything special will
            be escaped (at least in HTML, some text output format
            would possibly do nothing here)
        """
        return ""



class MoinFormatter(MoinFormatterBase):
    """
        Send HTML data.
    """

    hardspace = '&nbsp;'

    def __init__(self, request, **kw):
        apply(MoinFormatterBase.__init__, (self, request), kw)
        self._in_li = 0
        self._in_code = 0
        self._in_code_area = 0
        self._in_code_line = 0
        self._code_area_num = 0
        self._code_area_state = ['', 0, -1, -1, 0]
        self._show_section_numbers = None
        self._content_ids = []
        self.pagelink_preclosed = False
        self._is_included = kw.get('is_included',False)
        self.request = request
        self.cfg = request.cfg

        if not hasattr(request, '_fmt_hd_counters'):
            request._fmt_hd_counters = []

    def _langAttr(self):
        result = ''
        #lang = self.request.current_lang
        #if lang != self.cfg.default_lang:
        #    result = ' lang="%s" dir="%s"' % (lang, i18n.getDirection(lang))

        return result

    def startContent(self, content_id='content', **kwargs):
        if content_id!='content':
            aid = 'top_%s' % (content_id,)
        else:
            aid = 'top'
        self._content_ids.append(content_id)
        return '<div id="%s"%s>\n%s\n' % (content_id, self._langAttr(),
                                          self.anchordef(aid))

    def endContent(self):
        try:
            cid = self._content_ids.pop()
        except IndexError:
            cid = 'content'
        if cid!='content':
            aid = 'bottom_%s' % (cid,)
        else:
            aid = 'bottom'
        return '%s\n</div>\n' % self.anchordef(aid)

    def lang(self, on, lang_name):
        """ Insert text with specific lang and direction.
        
            Enclose within span tag if lang_name is different from
            the current lang    
        """
        
        if lang_name != self.request.current_lang:
            dir = i18n.getDirection(lang_name)
            return ['<span lang="%(lang_name)s" dir="%(dir)s">' % {
                'lang_name': lang_name, 'dir': dir},
                    '</span>'] [not on]
        
        return ''            
                
    def sysmsg(self, on, **kw):
        return ['\n<div class="message">', '</div>\n'][not on]

    
    # Links ##############################################################
    
    def pagelink(self, on, pagename='', **kw):
        """ Link to a page.

            See wikiutil.link_tag() for possible keyword parameters.
        """
        apply(MoinFormatterBase.pagelink, (self, on, pagename), kw)
        page = Page(self.request, pagename, formatter=self);
        
        if self.request.user.show_nonexist_qm and on and not page.exists():
            self.pagelink_preclosed = True
            return (page.link_to(self.request, on=1, **kw) +
                    self.text("?") +
                    page.link_to(self.request, on=0, **kw))
        elif not on and self.pagelink_preclosed:
            self.pagelink_preclosed = False
            return ""
        else:
            return page.link_to(self.request, on=on, **kw)

    def interwikilink(self, on, interwiki='', pagename='', **kw):
        if not on: return '</a>'
        
        wikitag, wikiurl, wikitail, wikitag_bad = wikiutil.resolve_wiki(self.request, '%s:%s' % (interwiki, pagename))
        wikiurl = wikiutil.mapURL(self.request, wikiurl)
        href = wikiutil.join_wiki(wikiurl, wikitail)

        # return InterWiki hyperlink
        if wikitag_bad:
            html_class = 'badinterwiki'
        else:
            html_class = 'interwiki'

        icon = ''
        if self.request.user.show_fancy_links:
            icon = self.request.theme.make_icon('interwiki', {'wikitag': wikitag}) 
        return (self.url(1, href, title=wikitag, unescaped=1,
                        pretty_url=kw.get('pretty_url', 0), css = html_class) +
                icon)

    def url(self, on, url=None, css=None, **kw):
        """
            Keyword params:
                title - title attribute
                ... some more (!!! TODO) 
        """
        #url = wikiutil.mapURL(self.request, url)
        pretty = kw.get('pretty_url', 0)
        title = kw.get('title', None)

        #if not pretty and wikiutil.isPicture(url):
        #    # XXX
        #    return '<img src="%s" alt="%s">' % (url,url)

        # create link
        if not on:
            return '</a>'
        str = '<a'
        if css: str = '%s class="%s"' % (str, css)
        if title: str = '%s title="%s"' % (str, title)
        str = '%s href="%s">' % (str, wikiutil.escape(url, 1))

        type = kw.get('type', '')

        if type=='www':
            str = '%s%s ' % (str, self.icon("www"))
        elif type=='mailto':
            str = '%s%s ' % (str, self.icon('mailto'))

        return str

    def anchordef(self, id):
        return '<a id="%s"></a>' % (id, )

    def anchorlink(self, on, name='', id = None):
        extra = ''
        if id:
            extra = ' id="%s"' % id
        return ['<a href="#%s"%s>' % (name, extra), '</a>'][not on]

    # Text and Text Attributes ###########################################
    
    def _text(self, text):
        if self._in_code:
            return wikiutil.escape(text).replace(' ', self.hardspace)
        return wikiutil.escape(text)

    def strong(self, on):
        return ['<strong>', '</strong>'][not on]

    def emphasis(self, on):
        return ['<em>', '</em>'][not on]

    def underline(self, on):
        return ['<u>', '</u>'][not on]

    def highlight(self, on):
        return ['<strong class="highlight">', '</strong>'][not on]

    def sup(self, on):
        return ['<sup>', '</sup>'][not on]

    def sub(self, on):
        return ['<sub>', '</sub>'][not on]

    def code(self, on):
        self._in_code = on
        return ['<tt>', '</tt>'][not on]

    def preformatted(self, on):
        MoinFormatterBase.preformatted(self, on)
        return ['<pre>', '</pre>'][not on]

    def small(self, on):
        return ['<small>', '</small>'][not on]
                                                                                
    def big(self, on):
        return ['<big>', '</big>'][not on]

    def code_area(self, on, code_id, code_type='code', show=0, start=-1, step=-1):
        res = ''
        ci = self.request.makeUniqueID('CA-%s_%03d' % (code_id, self._code_area_num))
        if on:
            self._in_code_area = 1
            self._in_code_line = 0
            self._code_area_state = [ci, show, start, step, start]
            if self._code_area_num == 0 and self._code_area_state[1] >= 0:
                res += """<script language='JavaScript'>
function isnumbered(obj){
  return obj.childNodes.length && obj.firstChild.childNodes.length && obj.firstChild.firstChild.className == 'LineNumber';
}
function nformat(num,chrs,add){
  var nlen = Math.max(0,chrs-(''+num).length), res = '';
  while (nlen>0) { res += ' '; nlen-- }
  return res+num+add;
}
function addnumber(did,nstart,nstep){
  var c = document.getElementById(did), l = c.firstChild, n = 1;
  if (!isnumbered(c))
    if (typeof nstart == 'undefined') nstart = 1;
    if (typeof nstep  == 'undefined') nstep = 1;
    n = nstart;
    while (l != null){
      if (l.tagName == 'SPAN'){
        var s = document.createElement('SPAN');
        s.className = 'LineNumber'
        s.appendChild(document.createTextNode(nformat(n,4,' ')));
        n += nstep;
        if (l.childNodes.length)
          l.insertBefore(s, l.firstChild)
        else
          l.appendChild(s)
      }
      l = l.nextSibling;
    }
  return false;
}
function remnumber(did){
  var c = document.getElementById(did), l = c.firstChild;
  if (isnumbered(c))
    while (l != null){
      if (l.tagName == 'SPAN' && l.firstChild.className == 'LineNumber') l.removeChild(l.firstChild);
      l = l.nextSibling;
    }
  return false;
}
function togglenumber(did,nstart,nstep){
  var c = document.getElementById(did);
  if (isnumbered(c)) {
    remnumber(did);
  } else {
    addnumber(did,nstart,nstep);
  }
  return false;
}
</script>
"""
            res += '<div class="codearea">'
            if self._code_area_state[1] >= 0:
                res += '<script>document.write(\'<a href="#" onClick="return togglenumber(\\\'%s\\\',%d,%d);" class="codenumbers">1,2,3</a>\')</script>' % (self._code_area_state[0], self._code_area_state[2], self._code_area_state[3])
            res += '<pre id="%s" class="codearea">' % (self._code_area_state[0], )
        else:
            res = ''
            if self._in_code_line:
                res += self.code_line(0)
            res += '</pre>'
            if self._code_area_state[1] >= 0:
                res += '<script>document.write(\'<a href="#" onClick="return togglenumber(\\\'%s\\\',%d,%d);" class="codenumbers">1,2,3</a>\')</script>' % (self._code_area_state[0], self._code_area_state[2], self._code_area_state[3])
            res += '</div>'
            self._in_code_area = 0
            self._code_area_num += 1
        return res

    def code_line(self, on):
        res = ''
        if not on or (on and self._in_code_line):
            res += '</span>\n'
        if on:
            res += '<span class="line">'
            if self._code_area_state[1] > 0:
                res += '<span class="LineNumber">%4d </span>' % (self._code_area_state[4], )
                self._code_area_state[4] += self._code_area_state[3]
        self._in_code_line = on != 0
        return res

    def code_token(self, on, tok_type):
        return ['<span class="%s">' % tok_type, '</span>'][not on]

    # Paragraphs, Lines, Rules ###########################################
    
    def linebreak(self, preformatted=1):
        if self._in_code_area:
            preformatted = 1
        return ['\n', '<br>\n'][not preformatted]

    def paragraph(self, on):
        #if self._terse:
        #    return ''
        MoinFormatterBase.paragraph(self, on)
        if self._in_li:
            self._in_li = self._in_li + 1
        result = ['<p%s>' % self._langAttr(), '\n</p>'][not on]
        return '%s\n' % result
    
    def rule(self, size=0):
        if size:
            return '<hr size="%d">\n' % (size,)
        else:
            return '<hr>\n'

    def icon(self, type):
        return '' #self.request.theme.make_icon(type)

    def smiley(self, text):
        w, h, b, img = config.smileys[text.strip()]
        href = img
        if not href.startswith('/'):
            href = self.request.theme.img_url(img)
        return self.image(src=href, alt=text, width=str(w), height=str(h))

    # Lists ##############################################################

    def number_list(self, on, type=None, start=None):
        if on:
            attrs = ''
            if type: attrs += ' type="%s"' % (type,)
            if start is not None: attrs += ' start="%d"' % (start,)
            result = '<ol%s%s>' % (self._langAttr(), attrs)
        else:    
            result = '</ol>\n'
        return '%s\n' % result
    
    def bullet_list(self, on):
        result = ['<ul%s>' % self._langAttr(), '</ul>\n'][not on]
        return '%s\n' % result

    def listitem(self, on, **kw):
        """ List item inherit its lang from the list. """
        self._in_li = on != 0
        if on:
            css_class = kw.get('css_class', None)
            attrs = ''
            if css_class: attrs += ' class="%s"' % (css_class,)
            style = kw.get('style', None)
            if style:  attrs += ' style="%s"' % style
            result = '<li%s>' % (attrs,)
        else:
            result = '</li>'
        return '%s\n' % result

    def definition_list(self, on):
        result = ['<dl>', '</dl>'][not on]
        return '%s\n' % result

    def definition_term(self, on):
        return ['<dt%s>' % (self._langAttr()), '</dt>'][not on]

    def definition_desc(self, on):
        return ['<dd%s>\n' % self._langAttr(), '</dd>\n'][not on]

    def heading(self, on, depth, id = None, **kw):
        # remember depth of first heading, and adapt counting depth accordingly
        if not self._base_depth:
            self._base_depth = depth

        count_depth = max(depth - (self._base_depth - 1), 1)

        # check numbering, possibly changing the default
        if self._show_section_numbers is None:
            self._show_section_numbers = 0 #self.cfg.show_section_numbers
            numbering = self.request.getPragma('section-numbers', '').lower()
            if numbering in ['0', 'off']:
                self._show_section_numbers = 0
            elif numbering in ['1', 'on']:
                self._show_section_numbers = 1
            elif numbering in ['2', '3', '4', '5', '6']:
                # explicit base level for section number display
                self._show_section_numbers = int(numbering)

        heading_depth = depth + 1

        # closing tag
        if not on:
            return '</h%d>' % heading_depth


        # create section number
        number = ''
        if self._show_section_numbers:
            # count headings on all levels
            self.request._fmt_hd_counters = self.request._fmt_hd_counters[:count_depth]
            while len(self.request._fmt_hd_counters) < count_depth:
                self.request._fmt_hd_counters.append(0)
            self.request._fmt_hd_counters[-1] = self.request._fmt_hd_counters[-1] + 1
            number = '.'.join(map(str, self.request._fmt_hd_counters[self._show_section_numbers-1:]))
            if number: number += ". "

        id_text = ''
        if id:
          id_text = ' id="%s"' % id

        result = '<h%d%s>' % (heading_depth, id_text)
        if 0: #self.request.user.show_topbottom:
            # TODO change top/bottom refs to content-specific top/bottom refs?
            result = ("%s%s%s%s%s%s%s%s" %
                      (result,
                       kw.get('icons',''),
                       self.url(1, "#bottom", unescaped=1),
                       self.icon('bottom'),
                       self.url(0),
                       self.url(1, "#top", unescaped=1),
                       self.icon('top'),
                       self.url(0)))
        return "%s%s%s" % (result, kw.get('icons',''), number)

    
    # Tables #############################################################

    # TODO: find better solution for bgcolor, align, valign (deprecated in html4)
    # do not remove current code before making working compliant code

    _allowed_table_attrs = {
        'table': ['class', 'width', 'bgcolor'],
        'row': ['class', 'width', 'align', 'valign', 'bgcolor'],
        '': ['colspan', 'rowspan', 'class', 'width', 'align', 'valign', 'bgcolor'],
    }

    def _checkTableAttr(self, attrs, prefix):
        if not attrs: return ''

        result = ''
        for key, val in attrs.items():
            if prefix and key[:len(prefix)] != prefix: continue
            key = key[len(prefix):]
            if key not in self._allowed_table_attrs[prefix]: continue
            result = '%s %s=%s' % (result, key, val)
        return result

    def table(self, on, attrs={}):
        if on:
            # Enclose table inside a div to get correct alignment
            # when using language macros
            attrs = attrs and attrs.copy() or {}
            result = '\n<div%(lang)s>\n<table%(tableAttr)s>' % {
                'lang': self._langAttr(),
                'tableAttr': self._checkTableAttr(attrs, 'table')
            }
        else:
            result = '</table>\n</div>'
        return '%s\n' % result
    
    def table_row(self, on, attrs={}):
        if on:
            result = '<tr%s>' % self._checkTableAttr(attrs, 'row')
        else:
            result = '</tr>'
        return '%s\n' % result

    def table_cell(self, on, attrs={}):
        # ensure table cells have a class so we can style them separate
        # from skin layout tables
        if not attrs.get('class',''): attrs['class'] = 'content'
        if on:
            result = '<td%s>' % self._checkTableAttr(attrs, '')
        else:
            result = '</td>'
        return '%s\n' % result

    def escapedText(self, text):
        return wikiutil.escape(text)


def escape(s, quote=0):
    """ Escape possible html tags
    
    Replace special characters '&', '<' and '>' by SGML entities.
    (taken from cgi.escape so we don't have to include that, even if we
    don't use cgi at all)

    FIXME: should return string or unicode?
    
    @param s: string to escape
    @param quote: bool, should transform '\"' to '&quot;'
    @rtype: string
    @return: escaped version of string
    """
    if not isinstance(s, (str, unicode)):
        s = str(s)

    # Must first replace &
    s = s.replace("&", "&amp;")

    # Then other...
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
    return s
    
def parseAttributes(request, attrstring, endtoken=None, extension=None):
    """
    Parse a list of attributes and return a dict plus a possible
    error message.
    If extension is passed, it has to be a callable that returns
    None when it was not interested into the token, '' when all was OK
    and it did eat the token, and any other string to return an error
    message.
    
    @param request: the request object
    @param attrstring: string containing the attributes to be parsed
    @param endtoken: token terminating parsing
    @param extension: extension function -
                      gets called with the current token, the parser and the dict
    @rtype: dict, msg
    @return: a dict plus a possible error message
    """
    import shlex, StringIO

    _ = request.getText

    parser = shlex.shlex(StringIO.StringIO(attrstring))
    parser.commenters = ''
    msg = None
    attrs = {}

    while not msg:
        try:
            key = parser.get_token()
        except ValueError, err:
            msg = str(err)
            break
        if not key: break
        if endtoken and key == endtoken: break

        # call extension function with the current token, the parser, and the dict
        if extension:
            msg = extension(key, parser, attrs)
            if msg == '': continue
            if msg: break

        try:
            eq = parser.get_token()
        except ValueError, err:
            msg = str(err)
            break
        if eq != "=":
            msg = _('Expected "=" to follow "%(token)s"') % {'token': key}
            break

        try:
            val = parser.get_token()
        except ValueError, err:
            msg = str(err)
            break
        if not val:
            msg = _('Expected a value for key "%(token)s"') % {'token': key}
            break

        key = escape(key) # make sure nobody cheats

        # safely escape and quote value
        if val[0] in ["'", '"']:
            val = escape(val)
        else:
            val = '"%s"' % escape(val, 1)

        attrs[key.lower()] = val

    return attrs, msg or ''

def isPicture(url):
    """
    Is this a picture's url?
    
    @param url: the url in question
    @rtype: bool
    @return: true if url points to a picture
    """
    extpos = url.rfind(".")
    return extpos > 0 and url[extpos:].lower() in ['.gif', '.jpg', '.jpeg', '.png']



class MoinWikiUtil: pass
wikiutil = MoinWikiUtil()
wikiutil.escape = escape
wikiutil.parseAttributes = parseAttributes
wikiutil.isPicture = isPicture

class MoinPage:
    page_name = ''

def render_moin_markup(text):
    req = MoinRequest()
    formatter = MoinFormatter(req)
    formatter.setPage(MoinPage())
    MoinParser(text,req).format(formatter)
    return unicode(req)

#print render_moin_markup("'''strong'''")

######################################################################

registerPageType(PageTypeMoin)

# backwards compatibility - need this here for old zodb objects
ZwikiMoinPageType = PageTypeMoin
