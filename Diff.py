######################################################################
# diff experiments
#
# todo
# separate out html vs. email diff methods
#
# this is a mess.
# newly promoted to Most Crufty
# needs to be refactored and made testable

from __future__ import nested_scopes
from string import join, split, atoi
import re
from struct import pack, unpack

from DocumentTemplate.DT_Util import html_quote
from OFS.History import historicalRevision
# Tim Peters' ndiff is now python 2.1's difflib module
# use the former for compatibility with older zopes
# XXX we don't support 1.5.2 now, change
from OFS import ndiff

from Defaults import MAX_OLD_LINES_DISPLAY, MAX_NEW_LINES_DISPLAY

def ISJUNK(line, pat=re.compile(r"\s*$").match):
    return pat(line) is not None

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


class DiffSupport:
    """
    I provide methods for browsing revision diffs to ZWikiPage.
    """

    def diff(self,revA=1,revB=0,showSteps=0,REQUEST=None,
             test=None, # for testing
             ):
        """
        Display a diff between two revisions of this page, as a web page.
        
        Uses the diffform template. See rawDiff for more.

        XXX should skip uninteresting transactions
        if re.search(r'(/edit|/comment|/append|PUT)',lastrevision['description']):
        """
        t = test or self.htmlDiff(revA=revA,revB=revB)
        return self.diffform(revA,t,REQUEST=REQUEST)

    def prevDiff(self,currentRevision):
        """
        helpers for form buttons
        """
        return self.diff(int(currentRevision)+1,int(currentRevision))

    def nextDiff(self,currentRevision):
        """
        helpers for form buttons
        """
        return self.diff(int(currentRevision)-1,int(currentRevision)-2)

    def lasttext(self, versionsBack=1):
        """
        Return the text of the last or an earlier revision of this page.
        """
        versionsBack = int(versionsBack)
        try:
            # problem here - manage_change_history only gets the last
            # 20 revisions
            lastrevision = self.manage_change_history()[versionsBack]
            key = lastrevision['key']
            serial=apply(pack, ('>HHHH',)+tuple(map(atoi, split(key,'.'))))
            lastself=historicalRevision(self, serial)
            return lastself.text()
        except:
            return '' # we don't have a version that old

    def revert(self, currentRevision, REQUEST=None):
        """
        Revert the most recent change
        """
        lastrevision = self.manage_change_history()[int(currentRevision)]
        key = lastrevision['key']
        serial=apply(pack, ('>HHHH',)+tuple(map(atoi, split(key,'.'))))
        lastself=historicalRevision(self, serial)
        self.setText(lastself.text())
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(self.wiki_page_url())

    def lastlog(self, versionsBack=0, withQuotes=0):
        """
        Get the log note from an earlier revision of this page.

        Just a quick helper for diff browsing.
        """
        versionsBack = int(versionsBack)
        try:
            # problem here - manage_change_history only gets the last
            # 20 revisions
            note = self.manage_change_history()[versionsBack]['description']
            match = re.search(r'"(.*)"',note)
            if match:
                if withQuotes: return match.group()
                else: return match.group(1)
            else:
                return ''
        except:
            return '' # we don't have a version that old

    def htmlDiff(self,revA=1,revB=0,a=None,b=None):
        """
        Generate a readable HTML-formatted diff of this page's revisions.

        Revisions are numbered backwards from the latest (0).
        Alternately, a and/or b texts can be specified.

        We don't bother abbreviating text segments like textDiff does.
        Should it use a page template ?
        """
        # XXX doesn't allow a=''
        a = a or self.lasttext(versionsBack=revA)
        b = b or self.lasttext(versionsBack=revB)
        a = split(a,'\n')
        b = split(b,'\n')
        r = []
        add, addm = r.append, r.extend
        # diffform encloses all this in a pre, so need to avoid line
        # breaks for now
        def addnobr(s): r[-1] += s
        for tag, alo, ahi, blo, bhi in self.rawDiff(a,b):
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

    def textDiff(self,revA=1,revB=0,a=None,b=None, verbose=1):
        """
        Generate readable a plain text diff of this page's revisions.

        This should optimize for human readability, as people may be
        getting a lot of these in mail-outs.

        Revisions are numbered backwards from the latest (0).
        Alternately, a and/or b texts can be specified.
        verbose adds more decoration.

        Each text segment is abbreviated according to built in constants,
        to avoid eg generating monster mail-outs. This can be annoying.
        """
        a = a or self.lasttext(versionsBack=revA)
        b = b or self.lasttext(versionsBack=revB)
        a = split(a,'\n')
        b = split(b,'\n')
        r = []
        add, addm = r.append, r.extend
        for tag, alo, ahi, blo, bhi in self.rawDiff(a,b):
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

    def rawDiff(self,a,b):
        """
        Return a diff between two texts, as difflib opcodes.
        """
        return ndiff.SequenceMatcher(
            #isjunk=lambda x: x in " \\t", # requires newer difflib
            isjunk=ISJUNK,
            a=a,
            b=b).get_opcodes()

    # wikifornow stuff - roll em in, sort em out later
#    def wfn_get_page_history(self, mode='condensed',
#                         batchsize=30, first=0, last=30):
#        """\
#        Return history records for a page, culling according to mode param.
#
#        'complete': all records.
#
#        'condensed': Omit showing prior versions of page replaced
#                     subsequently and soon after by the same person
#                     using same (possibly empty) log entry
#
#        Currently 
#        """
#        r = self._p_jar.db().history(self._p_oid, None, 5000)
#        for i in range(len(r)): r[i]['tacked_on_index'] = i
#
#        if mode == 'complete':
#            pass
#        elif mode == 'condensed':
#            # Each entry may:
#            #  - either continue an existing session or start a new one, and
#            #  - either be a landmark or not.
#            got = []
#            carrying = None
#            prevdescr = None
#            # Put in least-recent-first order:
#            r.reverse()
#            for entry in r:
#
#                curdescr = split(entry['description'], '\012')[1:]
#
#                # Handle prior retained stuff:
#                if carrying:
#                    if carrying['user_name'] != entry['user_name']:
#                        # Different user:
#                        got.append(carrying)
#                    elif curdescr != prevdescr:
#                        # Different log entry:
#                        got.append(carrying)
#                    else:
#                        itime, ctime = entry['time'], carrying['time']
#                        if type(itime) == FloatType:
#                            itime = entry['time'] = DateTime(itime)
#                        if type(ctime) == FloatType:
#                            ctime = carrying['time'] = DateTime(ctime)
#                        if (float(itime - ctime) * 60 * 24) > 30:
#                            # Enough time elapsed:
#                            # XXX klm "Enough time" should be configurable...
#                            got.append(carrying)
#
#                # Old-session, if any, was handled - move forward:
#                carrying = entry
#                prevdescr = curdescr
#
#            if carrying:
#                # Retain final item
#                got.append(carrying)
#
#            # Put back in most-recent-first order:
#            got.reverse()
#            r = got
#        else:
#            raise ValueError, "Unknown mode '%s'" % mode
#
#        for d in r:
#            if type(d['time']) == FloatType:
#                d['time'] = DateTime(d['time'])
#            d['key']=join(map(str, unpack(">HHHH", d['serial'])),'.')
#
#        r=r[first:first+batchsize+1]
#
#        return r
#    def wfn_history_copy_page_to_present(self, keys=[], REQUEST=None):
#        """Create a new object copy with the contents of an historic copy."""
#        request=getattr(self, 'REQUEST', None)
#        if not self.isAllowed('edit', request):
#            raise 'Unauthorized', "You're not allowed to edit this page"
#        self.manage_historyCopy(keys=keys)
#        if REQUEST is not None:
#            REQUEST.RESPONSE.redirect(self.wiki_page_url())
#    def wfn_history_compare_versions(self, keys=[], REQUEST=None):
#        """Do history comparisons.
#
#        Mostly stuff adapted from OFS.History - manage_historicalComparison() 
#        and manage_historyCompare(), with a bit of direct calling of
#        html_diff."""
#        from OFS.History import historicalRevision, html_diff
#        if not keys:
#            raise HistorySelectionError, (
#                "No historical revision was selected.<p>")
#        if len(keys) > 2:
#            raise HistorySelectionError, (
#                "Only two historical revision can be compared<p>")
#        
#        serial=apply(pack, ('>HHHH',)+tuple(map(string.atoi,
#                                                split(keys[-1],'.'))))
#        rev1=historicalRevision(self, serial)
#        
#        if len(keys)==2:
#            serial=apply(pack,
#                         ('>HHHH',)+tuple(map(string.atoi,
#                                              split(keys[0],'.'))))
#
#            rev2=historicalRevision(self, serial)
#        else:
#            rev2=self
#
#        dt1=DateTime(rev1._p_mtime)
#        dt2=DateTime(rev2._p_mtime)
#        t1, t2 = rev1._st_data, rev2._st_data
#        if t1 is None or t2 is None:
#            t1, t2 = rev1.xread(), rev2.xread()
#        top = self._manage_historyComparePage(
#            self, REQUEST,
#            dt1=dt1, dt2=dt2,
#            historyComparisonResults=html_diff(t1, t2),
#            manage_tabs=self.standard_wiki_header)
#        bottom = self.standard_wiki_footer(self, REQUEST=REQUEST)
#        return top + bottom
#
#
#def dump(tag, x, lo, hi, r):
#    r1=[]
#    r2=[]
#    for i in xrange(lo, hi):
#        r1.append(tag)
#        r2.append(x[i])
#    r.append("<tr>\n"
#            "<td valign=top width=1%%><pre>\n%s\n</pre></td>\n"
#            "<td valign=top width=99%%><pre>\n%s\n</pre></td>\n"
#            "</tr>\n"
#            % (join(r1,'\n'), html_quote(join(r2, '\n'))))
#
#def replace(x, xlo, xhi, y, ylo, yhi, r):
#
#    rx1=[]
#    rx2=[]
#    for i in xrange(xlo, xhi):
#        rx1.append('-')
#        rx2.append(x[i])
#
#    ry1=[]
#    ry2=[]
#    for i in xrange(ylo, yhi):
#        ry1.append('+')
#        ry2.append(y[i])
#
#
#    r.append("<tr>\n"
#            "<td valign=top width=1%%><pre>\n%s\n%s\n</pre></td>\n"
#            "<td valign=top width=99%%><pre>\n%s\n%s\n</pre></td>\n"
#            "</tr>\n"
#            % (join(rx1, '\n'), join(ry1, '\n'),
#               html_quote(join(rx2, '\n')), html_quote(join(ry2, '\n'))))

