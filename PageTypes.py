import string, re
from string import split,join,find,lower,rfind,atoi,strip,lstrip
from urllib import quote, unquote

import StructuredText
from StructuredText.DocumentWithImages import DocumentWithImages
try: from StructuredText.DocumentClass import StructuredTextTable
except ImportError: pass #older zope, won't need it

from Utils import BLATHER, html_quote, html_unquote, formattedTraceback, \
     ZOPEVERSION
try:
    # start headings at level 2, not 3; will affect all rst clients
    # XXX not working
    import reStructuredText # import this one first
    import docutils.writers.html4zope
    docutils.writers.html4zope.default_level = 2
except ImportError:
    reStructuredText = None
    BLATHER('could not import reStructuredText, will not be available')
from WWML import translate_WMML
from PurpleNumbers import add_purple_numbers_to
from Regexps import dtmlorsgmlexpr, footnoteexpr
from LocalizerSupport import _, N_


# XXX temporary hack, used for placing subtopics in the page. Supposed to
# be secret, invisible, and never encountered by users. Ha!
MIDSECTIONMARKER = 'ZWIKIMIDSECTION'

# PAGE TYPES
# these objects encapsulate various kinds of
# parsing/formatting/rendering/processing behaviour for a particular
# zwiki page type.  I've long felt that these might want to be
# objects; let's extract methods from ZWikiPage and see what happens.
# Answer: the State pattern. It should be cleaner overall.
# These have no state themselves, they are pure behaviour, and we
# generally pass in the page context as first argument.
# They could be singleton objects, unless that has problems with persistence..
# XXX check ram cache manager code

def yes(self): return 1
def no(self): return 0

class AbstractPageType:
    _id = None
    _name = None
    supportsStx = no
    supportsRst = no
    supportsWwml = no
    supportsWikiLinks = no
    supportsHtml = no
    supportsDtml = no
    supportsEpoz = no

    def id(self): return self._id
    def name(self): return self._name
    __call__ = id

    def __repr__(self):
        return "<%s '%s (%s)' at 0x%s>" % (self.__class__.__name__,
                                           self.id(),
                                           self.name(),
                                           hex(id(self))[2:])

    def preRender(self,page,text=None):
        """
        Do all the pre-rendering we can for page, or for a piece of text.
        """
        return text or page.read()

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        """
        Do any final (view-time) rendering for page.
        """
        return page.preRendered()

    def preRenderMessages(self,page):
        t = ''
        for m in page.messages(): t += self.preRenderMessage(page,m)
        if t: t = self.discussionSeparator(page) + t
        return t

    def preRenderMessage(self,page,msg):
        t = msg.get_payload()
        t = self.escapeEmailAddresses(page,t)
        t = self.renderCitationsIn(page,t)
        t = self.addCommentHeadingTo(page,t,msg)
        return t

    def escapeEmailAddresses(self,page,text):
        return re.sub(r'(?<!mailto:)\b(?!msg\d{14}-\d{4})(?<!msg\d{14}-)(\w[\w\-\+\.]*)@([\w\-\.]+)\.([\w\-\.]+)\b([^>]*<|$)', 
            lambda m: '<span class="nospam1">&#' + str(ord(m.groups()[0][0])) 
                + m.groups()[0][1:] 
                + '<!-- foobar --></span>&#64;<span class="nospam2">' 
                + m.groups()[1][0:-1] + '&#' + str(ord(m.groups()[1][-1])) 
                + ';&#46;' + m.groups()[2] + '</span>' + m.groups()[3], text)

    def renderCitationsIn(self,page,text):
        return text

    def addCommentHeadingTo(self,page,text,msg):
        return self.makeCommentHeading(page,
                                       msg.get('subject'),
                                       msg.get('from'),
                                       msg.get('date'),
                                       msg.get('message-id'),
                                       msg.get('in-reply-to')
                                       ) + text

    def makeCommentHeading(self, page,
                           subject, username, time, 
                           message_id=None,in_reply_to=None):
        heading = '\n\n'
        heading += '%s --' % (subject or '...')
        if username: heading = heading + '%s, ' % (username)
        heading += time
        heading += '\n\n'
        return heading

    def discussionSeparator(self,page):
        return '\n------------------------------------------------------------\n'

    def addPurpleNumbersTo(self,page,t):
        return add_purple_numbers_to(t,page)

class AbstractHtmlPageType(AbstractPageType):
    supportsHtml = yes

    def renderCitationsIn(self, page, t):
        inblock = 0
        blocklines = []
        blockend=0
        lines = string.split(t, '\n')
        t = ""
        for i in range(len(lines)):
            m = re.match(r'^\s*>\s?(.*)$', lines[i])
            if(m):
                if(not inblock):
                    t += string.join(lines[blockend:i],'\n')
                    t += '\n<blockquote type="cite">\n\n'
                inblock = 1
                blocklines.append(m.group(1))
            elif(inblock):
                inblock = 0
                blockend=i
                t += self.renderCitationsIn(page,string.join(blocklines, '\n'))
                t += '\n\n</blockquote>\n'
                blocklines = []
        t += string.join(lines[blockend:], '\n')
        return t 

    def makeCommentHeading(self, page,
                           subject, username, time, 
                           message_id=None,in_reply_to=None):
        heading = '\n\n'
        if message_id:
            # use the message id for linking, but strip the <>
            # and leave it unquoted, browsers can handle it
            heading += '<a name="msg%s"></a>\n' % \
                       re.sub(r'^<(.*)>$',r'\1',message_id)
        if page.inCMF():
            heading += \
              '<img src="discussionitem_icon.gif" style="border:none; margin:0" />'
        heading += '<b>%s</b> --' % (subject or '...') #more robust
        if username: heading = heading + '%s, ' % (username)
        if message_id:
            heading += ' <a href="%s#msg%s">%s</a>' % \
                       (page.page_url(),
                        re.sub(r'^<(.*)>$',r'\1',message_id),
                        html_quote(time))
            inreplytobit = '&in_reply_to='+quote(message_id)
        else:
            heading += html_quote(time)
            inreplytobit = ''
        heading += ' <a href="%s?subject=%s%s#bottom">reply</a>'\
                   % (page.page_url(),quote(subject or ''),inreplytobit)
        heading += '<br />\n'
        return heading

    def discussionSeparator(self,page):
        # we want to customize the heading style in the stylesheet..
        # but also have it look ok by default in plone, which has it's own..
        # without preventing it being overridden - perhaps b outside the span
        # will work
        return '\n\n<a name="comments"><br><b><span class="commentsheading">comments:</span></b></a>\n\n'
    
class ZwikiStxPageType(AbstractHtmlPageType):
    _id = 'msgstxprelinkdtmlfitissuehtml'
    _name = 'Structured Text'
    supportsStx = yes
    supportsWikiLinks = yes
    supportsHtml = yes
    supportsDtml = yes

    def renderStxIn(self,page,t):
        """
        Render some Structured Text into HTML, with our customizations.
        """
        t = str(t)        
        if ZOPEVERSION < (2,4):
            # final single-line paragraph becomes a heading if there are
            # trailing blank lines - strip them
            t = re.sub(r'(?m)\n[\n\s]*$', r'\n', t)
        # an initial single word plus period becomes a numeric bullet -
        # prepend a temporary marker to prevent
        # XXX use locale/wikichars from Regexps.py instead of A-z
        # XXX not working ?
        t = re.sub(r'(?m)^([ \t]*)([A-z]\w*\.)',
                      r'\1<!--NOSTX-->\2',
                      t)
        # :: quoting fails if there is whitespace after the :: - remove it
        t = re.sub(r'(?m)::[ \t]+$', r'::', t)
        # suppress stx footnote handling so we can do it our way later
        t = re.sub(footnoteexpr,r'<a name="ref\1">![\1]</a>',t)
        t = re.sub(r'(?m)\[',r'[<!--NOSTX-->',t)
        # let STX loose on it.. 
        try:
            if ZOPEVERSION < (2,4):
                t = str(StructuredText.HTML(t,level=2))
            else:
                # with a few more tweaks for STX NG
                t = StructuredText.HTMLWithImages(
                    MyDocumentWithImages(StructuredText.Basic(t)),
                    level=2)
        except:
            BLATHER('Structured Text rendering failed on page %s: %s' \
                 % (page.id(),formattedTraceback()))
            return '<pre>Structured Text rendering failed:\n%s</pre>' \
                   % (formattedTraceback())
        # clean up
        t = re.sub(r'(<|&lt;)!--NOSTX--(>|&gt;)', r'', t)
        # strip html & body added by some zope versions
        t = re.sub(
            r'(?sm)^<html.*<body.*?>\n(.*)</body>\n</html>\n',r'\1',t)
        return t

    def preRender(self, page, text=None):
        """
        Do as much up-front rendering work as possible and save it.
        
        For the STX page type, this means: format mbox-style messages,
        apply text formatting, format any purple numbers, and identify
        wiki links.
        
        This normally works on page's source, but can be also invoked on
        arbitrary text.
        """
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+ \
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.renderStxIn(page, t)
        if page.usingPurpleNumbers(): t = page.renderPurpleNumbersIn(t)
        t = page.markLinksIn(t)
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        """
        In the final render stage, done each at page view, we evaluate
        DTML (if allowed), render the wiki links, execute any fit test
        tables, add an issue properties form if this is an issue page,
        add a subtopics listing if enabled, and add the wiki page skin.
        """
        if page.dtmlAllowed():
            t = page.evaluatePreRenderedAsDtml(page,REQUEST,RESPONSE,**kw)
        else:
            t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        if page.hasFitTests(): t = page.runFitTestsIn(t)
        if page.isIssue(): t = page.addIssueFormTo(t)
        t = page.renderMidsectionIn(t)
        t = page.addSkinTo(t,**kw)
        return t

class ZwikiHtmlPageType(AbstractHtmlPageType):
    _id = 'dtmlhtml'
    _name = 'HTML'
    supportsHtml = yes
    supportsDtml = yes
    supportsEpoz = yes

    def preRender(self, page, text=None):
        t = text or (page.read()+'\n'+MIDSECTIONMARKER)
        t = page.applyWikiLinkLineEscapesIn(t)
        t = page.markLinksIn(t)
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        if page.dtmlAllowed() and page.hasDynamicContent():
            t = page.evaluatePreRenderedAsDtml(page,REQUEST,RESPONSE,**kw)
        else:
            t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        t = page.renderMidsectionIn(t)
        t = page.addSkinTo(t,**kw)
        return t

class ZwikiRstPageType(AbstractPageType):
    _id = 'msgrstprelinkfitissue'
    _name = 'reStructured Text'
    supportsRst = yes
    supportsWikiLinks = yes

    def renderRstIn(self,t):
        if reStructuredText:
            return reStructuredText.HTML(t,report_level=0) # doesn't work:(
        else:
            return "<pre>Error: could not import reStructuredText</pre>\n"+t

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+ \
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.renderRstIn(t)
        if page.usingPurpleNumbers(): t = page.renderPurpleNumbersIn(t)
        t = page.markLinksIn(t)
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        if page.hasFitTests(): t = page.runFitTestsIn(t)
        if page.isIssue(): t = page.addIssueFormTo(t)
        t = page.renderMidsectionIn(t)
        t = page.addSkinTo(t,**kw)
        return t

    def makeCommentHeading(self, page,
                           subject, username, time, 
                           message_id=None,in_reply_to=None):
        heading = '\n\n'
        heading += '**%s** --' % (subject or '...')
        if username: heading = heading + '%s, ' % (username)
        heading += time
        heading += '\n\n'
        return heading

    def discussionSeparator(self,page):
        return '\n\n------------------------------------------------------------\n\n'

class ZwikiWwmlPageType(AbstractPageType):
    _id = 'msgwwmlprelinkfitissue'
    _name = 'WikiWikiWeb markup'
    supportsWwml = yes
    supportsWikiLinks = yes

    def renderWwmlIn(self,t):
        return translate_WMML(html_quote(t))

    def preRender(self, page, text=None):
        t = text or (page.document()+'\n'+MIDSECTIONMARKER+\
                     self.preRenderMessages(page))
        t = page.applyWikiLinkLineEscapesIn(t)
        t = self.renderWwmlIn(t)
        if page.usingPurpleNumbers(): t = page.renderPurpleNumbersIn(t)
        t = page.markLinksIn(t)
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        t = page.renderMarkedLinksIn(t)
        if page.hasFitTests(): t = page.runFitTestsIn(t)
        if page.isIssue(): t = page.addIssueFormTo(t)
        t = page.renderMidsectionIn(t)
        t = page.addSkinTo(t,**kw)
        return t

class ZwikiPlaintextPageType(AbstractPageType):
    _id = 'plaintext'
    _name = 'Plain text'

    def renderPlaintextIn(self,t):
        return "<pre>\n%s\n</pre>\n" % html_quote(t)

    def preRender(self, page, text=None):
        t = text or page.read()
        t = self.renderPlaintextIn(t)
        if not text: t += '\n'+MIDSECTIONMARKER
        t = self.escapeEmailAddresses(page,t)
        return t

    def render(self, page, REQUEST={}, RESPONSE=None, **kw):
        t = page.preRendered()
        t = page.renderMidsectionIn(t)
        t = page.addSkinTo(t,**kw)
        return t

# more structured text customizations
class MyDocumentWithImages(DocumentWithImages):

    # 1. leave dtml alone (ignore '' within SGML tags)
    def doc_sgml(self,s,expr=re.compile(dtmlorsgmlexpr).search):
        r = expr(s)
        if r:
            start,end = r.span()
            text = s[start:end]
            return (StructuredText.DocumentClass.StructuredTextSGML(text),
                    start,
                    end)
    # we need SGML/DTML expressions to be first priority
    # doesn't look like ZopeIssue:432 will change
    # so we must hard-code STX element types and priorities here..
    # should mimic STXNG behaviour as closely as possible here
    text_types = [
        'doc_sgml',    
        'doc_literal',
        'doc_img',
        'doc_inner_link',
        'doc_named_link',
        'doc_href1',
        'doc_href2',
        'doc_strong',
        'doc_emphasize',
        'doc_underline',
        'doc_sgml',
        'doc_xref',
        ]

    # 2. allow + at table corners; makes emacs picture-mode editing easier
    def doc_table(self, paragraph,
                  expr = re.compile(r'\s*[+|][-+]+[+|]').match):
        text    = paragraph.getColorizableTexts()[0]
        m       = expr(text)
        
        subs = paragraph.getSubparagraphs()
        
        if not (m):
            return None
        rows = []
                
        spans   = []
        ROWS    = []
        COLS    = []
        indexes = []
        ignore  = []
        
        TDdivider   = re.compile(r'[-+]+').match
        THdivider   = re.compile(r'[=+]+').match
        col         = re.compile(r'\|').search
        innertable  = re.compile(r'(?![-=])[+|]([-+]+|[=+]+)[+|](?![-=])').search
        
        text = strip(text)
        rows = split(text,'\n')
        foo  = ""
        
        for row in range(len(rows)):
            rows[row] = strip(rows[row])
        
        # have indexes store if a row is a divider
        # or a cell part
        for index in range(len(rows)):
            tmpstr = rows[index][1:len(rows[index])-1]
            if TDdivider(tmpstr):
                indexes.append("TDdivider")
            elif THdivider(tmpstr):
                indexes.append("THdivider")
            else:
                indexes.append("cell")

        for index in range(len(indexes)):
            if indexes[index] is "TDdivider" or indexes[index] is "THdivider":
                ignore = [] # reset ignore
                #continue    # skip dividers

            tmp     = strip(rows[index])    # clean the row up
            tmp     = tmp[1:len(tmp)-1]     # remove leading + trailing |
            offset  = 0

            # find the start and end of inner
            # tables. ignore everything between
            if innertable(tmp):
                tmpstr = strip(tmp)
                while innertable(tmpstr):
                    start,end   = innertable(tmpstr).span()
                    if not (start,end-1) in ignore:
                        ignore.append((start,end-1))
                    tmpstr = " " + tmpstr[end:]

            # find the location of column dividers
            # NOTE: |'s in inner tables do not count
            #   as column dividers
            if col(tmp):
                while col(tmp):
                    bar         = 1   # true if start is not in ignore
                    start,end   = col(tmp).span()

                    if not start+offset in spans:
                        for s,e in ignore:
                            if start+offset >= s or start+offset <= e:
                                bar = None
                                break
                        if bar:   # start is clean
                            spans.append(start+offset)
                    if not bar:
                        foo = foo + tmp[:end]
                        tmp = tmp[end:]
                        offset = offset + end
                    else:
                        COLS.append((foo + tmp[0:start],start+offset))
                        foo = ""
                        tmp = " " + tmp[end:]
                        offset = offset + start
            if not offset+len(tmp) in spans:
                spans.append(offset+len(tmp))
            COLS.append((foo + tmp,offset+len(tmp)))
            foo = ""
            ROWS.append(COLS)
            COLS = []
        
        spans.sort()
        ROWS = ROWS[1:len(ROWS)]

        # find each column span
        cols    = []
        tmp     = []
        
        for row in ROWS:
            for c in row:
                tmp.append(c[1])
            cols.append(tmp)
            tmp = []
        
        cur = 1
        tmp = []
        C   = []
        for col in cols:
            for span in spans:
                if not span in col:
                    cur = cur + 1
                else:
                    tmp.append(cur)
                    cur = 1
            C.append(tmp)
            tmp = []
        
        for index in range(len(C)):
            for i in range(len(C[index])):
                ROWS[index][i] = (ROWS[index][i][0],C[index][i])
        rows = ROWS
        
        # label things as either TableData or
        # Table header
        TD  = []
        TH  = []
        all = []
        for index in range(len(indexes)):
            if indexes[index] is "TDdivider":
                TD.append(index)
                all.append(index)
            if indexes[index] is "THdivider":
                TH.append(index)
                all.append(index)
        TD = TD[1:]
        dividers = all[1:]
        #print "TD  => ", TD
        #print "TH  => ", TH
        #print "all => ", all, "\n"
        
        for div in dividers:
            if div in TD:
                index = all.index(div)
                for rowindex in range(all[index-1],all[index]):                    
                    for i in range(len(rows[rowindex])):
                        rows[rowindex][i] = (rows[rowindex][i][0],
                                             rows[rowindex][i][1],
                                             "td")
            else:
                index = all.index(div)
                for rowindex in range(all[index-1],all[index]):
                    for i in range(len(rows[rowindex])):
                        rows[rowindex][i] = (rows[rowindex][i][0],
                                             rows[rowindex][i][1],
                                             "th")
        
        # now munge the multi-line cells together
        # as paragraphs
        ROWS    = []
        COLS    = []
        for row in rows:
            for index in range(len(row)):
                if not COLS:
                    COLS = range(len(row))
                    for i in range(len(COLS)):
                        COLS[i] = ["",1,""]
                if TDdivider(row[index][0]) or THdivider(row[index][0]):
                    ROWS.append(COLS)
                    COLS = []
                else:
                    COLS[index][0] = COLS[index][0] + (row[index][0]) + "\n"
                    COLS[index][1] = row[index][1]
                    COLS[index][2] = row[index][2]
        
        # now that each cell has been munged together,
        # determine the cell's alignment.
        # Default is to center. Also determine the cell's
        # vertical alignment, top, middle, bottom. Default is
        # to middle
        rows = []
        cols = []
        for row in ROWS:
            for index in range(len(row)):
                topindent       = 0
                bottomindent    = 0
                leftindent      = 0
                rightindent     = 0
                left            = []
                right           = []                                    
                text            = row[index][0]
                text            = split(text,'\n')
                text            = text[:len(text)-1]
                align           = ""
                valign          = ""
                for t in text:
                    t = strip(t)
                    if not t:
                        topindent = topindent + 1
                    else:
                        break
                text.reverse()
                for t in text:
                    t = strip(t)
                    if not t:
                        bottomindent = bottomindent + 1
                    else:
                        break
                text.reverse()
                tmp   = join(text[topindent:len(text)-bottomindent],"\n")
                pars  = re.compile("\n\s*\n").split(tmp)
                for par in pars:
                    if index > 0:
                        par = par[1:]
                    par = split(par, ' ')
                    for p in par:
                        if not p:
                            leftindent = leftindent+1
                        else:
                            break
                    left.append(leftindent)
                    leftindent = 0
                    par.reverse()
                    for p in par:
                        if not p:
                            rightindent = rightindent + 1
                        else:
                            break
                    right.append(rightindent)
                    rightindent = 0
                left.sort()
                right.sort()

                if topindent == bottomindent:
                    valign="middle"
                elif topindent < 1:
                    valign="top"
                elif bottomindent < 1:
                    valign="bottom"
                else:
                    valign="middle"

                if left[0] < 1:
                    align = "left"
                elif right[0] < 1:
                    align = "right"
                elif left[0] > 1 and right[0] > 1:
                    align="center"
                else:
                    align="left"
                
                cols.append((row[index][0],row[index][1],align,valign,row[index][2]))
            rows.append(cols)
            cols = []
        return StructuredTextTable(rows,text,subs,indent=paragraph.indent)
            
MyDocumentWithImages = MyDocumentWithImages()
    
