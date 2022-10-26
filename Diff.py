"""
A diff-browsing view and utilities for use with History.
"""

from __future__ import nested_scopes
from string import join, split, atoi
import re
from struct import pack, unpack
import difflib

from DocumentTemplate.DT_Util import html_quote
from OFS.History import historicalRevision
from AccessControl import getSecurityManager, ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from Defaults import MAX_OLD_LINES_DISPLAY, MAX_NEW_LINES_DISPLAY
import Permissions
from Utils import get_transaction, BLATHER, formattedTraceback


class PageDiffSupport:
    """
    I provide methods for browsing a zwiki page's edit history details,
    showing differences between edits.
    """
    security = ClassSecurityInfo()

    def diff(self, rev=None, REQUEST=None):
        """
        Show what changed in the latest or specified revision of this page.
        
        Uses the diffform template.
        """
        if rev: brev = int(rev)
        else:   brev = self.revisionNumber()
        atext, btext = '', ''
        b = self.revision(brev)
        if b:
            btext = self.tounicode(b.text()) # nb old revisions might be utf-8
            a = b.previousRevision()
            if a:
                atext = self.tounicode(a.text())
        difftext     = htmldiff(atext,btext)
        # wiki links won't find their targets in the revisions folder
        # (unless prerendered is still intact). Oh well.
        bodytext = b(REQUEST=REQUEST,bare=1,show_subtopics=0)
        return self.diffform(brev, difftext, bodytext, REQUEST=REQUEST)

    def textDiff(self, a='', b='', verbose=1):
        """
        Generate a readable plain text diff for this page's last edit.

        Or, between two specified texts. See textdiff.
        """
        if not (a or b):
            b = self.text()
            arev = self.revision(self.previousRevisionNumber())
            a = arev and arev.text() or ''
        return textdiff(a,b,verbose)

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

