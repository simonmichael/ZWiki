## Script (Python) "toc"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=columns, headings=('Basics','Intermediate','Advanced'), colours=('#3F5ACE','red','black')
##title=
##
## Generates a multi-column table of contents for a wiki page
## SKWM inspired by silverorange.
## columns is a list of lists, usually three
## example: <dtml-var "toc(None, [], ['section1','section2'])">
## None means hide that column
## [] means show the column heading only
## section names are linked to #1, #2.. you should create those named anchors.
## headings and colours may be overridden


linkindex = 1

print """
<!-- toc macro start -->
<table border="0" width="100%%">
  <tr>
"""
columnwidth = 100/len(columns)
colindex = 0

for column in columns:

    print """
    <td valign="top" width="%s%%">
    """ % (columnwidth)

    if column is not None:
        heading, colour = headings[colindex], colours[colindex]

        print """
      <table border="0" cell padding="0" cellspacing="0" width="100%%" style="margin-bottom: 4px;">
        <tr>  
          <td bgcolor="%s" nowrap class="subtext"><div style="color: #FFFFFF; padding-top: 3px; padding-left: 6px; padding-right: 6px;"><strong>%s</strong></div></td>
          <td width="100%%">&nbsp;</td>
        </tr>
        <tr>
          <td bgcolor="%s"><img src="/p_/sp" width="2" height="1" hspace="65" alt="" /></td>
          <td colspan="2" bgcolor="%s"><img src="/p_/sp" width="3" height="3" alt="" /></td>
        </tr>
      </table>
      <div class="pagecontents" style="font-size:small;">
        <table>
          <tr>
            <td valign="top">
              <ol style="margin-top: 0; margin-bottom: 0;" class="subtext" start="%s">
        """ % (colour,heading,colour,colour,linkindex)

        for link in column:
            print """
                      <li><a href="#%s">%s</a></li>
            """ % (linkindex,link)
            linkindex += 1

        print """
              </ol>
            </td>
          </tr>
        </table>
      </div>
    </td>
        """

    else:
        print """
            &nbsp;
        """

    colindex += 1

print """
  </tr>
</table>
<!-- toc macro end -->

"""

return printed
