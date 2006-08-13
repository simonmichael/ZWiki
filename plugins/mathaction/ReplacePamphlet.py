"""
Replace pamphlet contents with embedded PDF

$Id: ReplacePamphlet.py,v 0.2 2005/11/12 Bill Page $

TODO:
	1) Provide a wiki folder property to override the path so that pamphlet,
	   dvi, and pdf files can be mapped to specific directories. Currently
	   defaults to 'imagesPath' for Zope/LatexWiki compatibility. But Apache
	   proxy or additional Zope external files systems would allow them to
	   be anywhere.
	2) Write pamphlet file to source code archive and do a check-in
	   Archive check-in controlled/disabled by a wiki folder property.
"""

import re, os, string
from util import imagesPath, workingDir

errorMessage = """\n<hr/><font size="-1" color="red">
Some or all expressions may not have rendered properly,
because Latex returned the following error:<br/><pre>%s</pre></font>"""
reConsts = re.MULTILINE+re.DOTALL

def replacePamphlet(page,body):
    from pamphletWrapper import renderPDF

    # Keep the comments after the end of the document
    doc = re.match(r'^(\\.*?\\end{document})(.*)$',body,reConsts)
    if doc:

# workingDir + fPath  = fDir
#                     + pageName = fName   (physical location)
# imagesPath + fPath  + pageName = fUrl    (logical location)

# Note: only works with http://wiki.axiom-developer.org/... now
# Need to fix this (somehow!) so that it works with url proxy aliases

      fPath = "/".join(page.wiki_base_url().split('/')[3:])
      fDir = os.path.join(workingDir,fPath)
      try:
        os.makedirs(fDir)
      except:
        pass
      pageName = page.title_or_id()
      fName = os.path.join(fDir,pageName)
      try:
        file = open(fName+'.pamphlet', 'w')
        file.write(doc.group(1))
        file.close()
      except:
        print "Can't save pamphlet file"
        raise
      pdf=re.match(r'.*\\usepackage\[.*(dvips|dvipdfm).*?\]{hyperref}',doc.group(1),reConsts)
      if pdf:
        pdfMethod=pdf.group(1)
      else:
        pdfMethod=''
      errors = renderPDF(fDir,pageName,pdfMethod)
      fUrl = os.path.join('/',imagesPath,fPath,pageName)
      return ('''
<table cellpadding=0 cellspacing=0 width="100%%">
<tr style="background-color:lightgrey">
<td align="left" width="50%%"><b>Download:</b>
<a href="%s.pdf">pdf</a>
<a href="%s.dvi">dvi</a>
<a href="%s.ps">ps</a>
<a href="%s.pamphlet">src</a>
<a href="%s.tex">tex</a>
<a href="%s.log">log</a></td>
</td>
<td align="right" width="50%%"><form action="%s/tangle" method="get">
<input type="submit" name="submit" value="tangle"/>
<select name="chunk" >%s</select></form></td>
</tr></table><br />
<div style="text-align:center;width:100%%"><img src="%s1.png" /></div>
''' %(fUrl,fUrl,fUrl,fUrl,fUrl,fUrl,
      page.page_url(), 
      '<option>*</option>\n'+''.join(['<option>%s</option>\n'%(m.group(1))
          for m in re.finditer(r'<<(.*?)>>=',doc.group(1))
          if m.group(1)<>'*']),  # we want * as default option
      fUrl)+
        ((errors and """\n<hr/><font size="-1" color="red">
Some or all of this page may not have rendered properly,
because of the following error:<br/><pre>%s</pre></font>
""" %(errors)) or ''),
        doc.group(2))
    else:
      # just comments
      return ('',body)

