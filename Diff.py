"""
Simple revisions support for zwiki pages.

Provides methods to look up and revert to old versions from the ZODB history,
and a diff-browsing form.

todo:
- clean up 
- separate out html vs. email diff methods

"""

from __future__ import nested_scopes
from string import join, split, atoi
import re
from struct import pack, unpack
import difflib

from DocumentTemplate.DT_Util import html_quote
from OFS.History import historicalRevision
from AccessControl import getSecurityManager, ClassSecurityInfo
from Globals import InitializeClass

from Defaults import MAX_OLD_LINES_DISPLAY, MAX_NEW_LINES_DISPLAY
import Permissions
from Utils import get_transaction, BLATHER, formattedTraceback


class PageDiffSupport:
    """
    I provide methods for browsing a zwiki page's edit history details,
    showing differences between edits.
    """
    security = ClassSecurityInfo()
    
    def diff(self,revA=1,revB=0,REQUEST=None,
             test=None, # for testing
             ):
        """
        Display a diff between two revisions of this page, as a web page.
        
        Uses the diffform template. See diffcodes for more.

        XXX should skip uninteresting transactions
        if re.search(r'(/edit|/comment|/append|PUT)',lastrevision['description']):
        """
        revA, revB = str(revA), str(revB)
        t = test or self.htmlDiff(revA=revA,revB=revB)
        return self.diffform(revA,t,REQUEST=REQUEST)

    def prevDiff(self,currentRevision):
        """A helper for the diffform view."""
        return self.diff(int(currentRevision)+1,int(currentRevision))

    def nextDiff(self,currentRevision):
        """A helper for the diffform view."""
        return self.diff(int(currentRevision)-1,int(currentRevision)-2)

    security.declareProtected(Permissions.View, 'revisionInfo')
    def revisionInfo(self, rev):
        """A helper for the diffform view, accesses some revision details."""
        old = self.pageRevision(rev)
        if old:
            return {
                'last_editor':old.last_editor,
                'last_edit_time':old.last_edit_time,
                'lastEditTime':old.lastEditTime(),
                }
        else:
            return None

    security.declareProtected(Permissions.View, 'lasttext')
    def lasttext(self, rev=1):
        """Return the text of the last or an earlier revision of this page."""
        revision = self.pageRevision(rev)
        return revision and revision.text() or ''
    
    def textDiff(self,revA=1,revB=0,a=None,b=None, verbose=1):
        """
        Generate readable a plain text diff of this page's revisions.

        Revisions are numbered backwards from the latest (0).
        Alternately, a and/or b texts can be specified.
        See textdiff.
        """
        a = a or self.lasttext(rev=revA)
        b = b or self.lasttext(rev=revB)
        return textdiff(a,b,verbose)

    def htmlDiff(self,revA=1,revB=0,a=None,b=None):
        """
        Generate a readable HTML-formatted diff of this page's revisions.

        Revisions are numbered backwards from the latest (0).
        Alternately, a and/or b texts can be specified.

        We don't bother abbreviating text segments like textDiff does.
        Should it use a page template ?

        See htmldiff.
        """
        # XXX doesn't allow a=''
        a = a or self.lasttext(rev=revA)
        b = b or self.lasttext(rev=revB)
        return htmldiff(a,b)

InitializeClass(PageDiffSupport)


def prefix(lines,prefix): return map(lambda x:prefix+x,lines)

def abbreviate(lines,prefix,maxlines=5):
    output = []
    if maxlines and len(lines) > maxlines:
        extra = len(lines) - maxlines
        for i in xrange(maxlines - 1):
            output.append(prefix + lines[i])
        output.append(prefix + "[%d more line%s...]" %
                      (extra, ((extra == 1) and '') or 's')) # not working
    else:
        for line in lines:
            output.append(prefix + line)
    return output

def addedtext(a,b):
    """Return any lines which are in b but not in a, according to difflib."""
    a = split(a,'\n')
    b = split(b,'\n')
    r = []
    for tag, alo, ahi, blo, bhi in diffcodes(a,b):
        if tag in ('insert','replace'): r.extend((b[blo:bhi]))
        else: pass
    return '\n' + join(r,'\n')

def diffcodes(a,b):
    """Return a diff between two texts, as difflib opcodes."""
    return difflib.SequenceMatcher(
        isjunk=re.compile(r"\s*$").match,
        a=a,
        b=b).get_opcodes()

def textdiff(a, b, verbose=1):
    """
    Generate readable a plain text diff between two texts.

    This should optimize for human readability, as people may be
    getting a lot of these in mail-outs.

    verbose adds more decoration.

    Each text segment is abbreviated according to built in constants,
    to avoid eg generating monster mail-outs. This can be annoying.
    """
    a = split(a,'\n')
    b = split(b,'\n')
    r = []
    add, addm = r.append, r.extend
    for tag, alo, ahi, blo, bhi in diffcodes(a,b):
        if tag == 'replace':
            if verbose: add('??changed:')
            addm(abbreviate(a[alo:ahi],'-',MAX_OLD_LINES_DISPLAY))
            addm(abbreviate(b[blo:bhi],'',MAX_NEW_LINES_DISPLAY))
            add('')
        elif tag == 'delete':
            if verbose: add('--removed:')
            addm(abbreviate(a[alo:ahi],'-',MAX_OLD_LINES_DISPLAY))
            add('')
        elif tag == 'insert':
            if verbose: add('++added:')
            addm(abbreviate(b[blo:bhi],'',MAX_NEW_LINES_DISPLAY))
            add('')
        else: # tag == 'equal'
            pass 
    return '\n' + join(r,'\n')

def htmldiff(a,b):
    """
    Generate a readable HTML-formatted diff between two texts.

    Revisions are numbered backwards from the latest (0).
    Alternately, a and/or b texts can be specified.

    We don't bother abbreviating text segments like textDiff does.
    Should it use a page template ?
    """
    # XXX doesn't allow a=''
    a = a or self.lasttext(rev=revA)
    b = b or self.lasttext(rev=revB)
    a = split(a,'\n')
    b = split(b,'\n')
    r = []
    add, addm = r.append, r.extend
    # diffform encloses all this in a pre, so need to avoid line
    # breaks for now
    def addnobr(s): r[-1] += s
    for tag, alo, ahi, blo, bhi in diffcodes(a,b):
        if tag == 'replace':
            add('<b>changed:</b>')
            addnobr('<span style="color:red;text-decoration:line-through">')
            # remember to html-quote the diff segments
            addm(prefix(map(html_quote, a[alo:ahi]),'-')) 
            addnobr('</span>')
            addnobr('<span style="color:green">')
            addm(map(html_quote, b[blo:bhi]))
            addnobr('</span>')
            add('')
        elif tag == 'delete':
            add('<b>removed:</b>')
            addnobr('<span style="color:red;text-decoration:line-through">')
            addm(prefix(map(html_quote, a[alo:ahi]),'-'))
            addnobr('</span>')
            add('')
        elif tag == 'insert':
            add('<b>added:</b>')
            addnobr('<span style="color:green">')
            addm(map(html_quote, b[blo:bhi]))
            addnobr('</span>')
            add('')
        else: # tag == 'equal'
            pass
    return '\n' + join(r,'\n')

