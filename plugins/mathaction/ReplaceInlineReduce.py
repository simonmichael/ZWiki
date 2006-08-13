
"""
ReplaceInlineReduce.py v. 0.2.3
  Replace REDICE command \\begin{reduce} \\end{reduce} blocks with LaTeX
"""

import re
from string import join

def replaceInlineReduce(body):
    from reduceWrapper import renderReduce
    errorMessage = """\n<hr/><font size="-1" color="red">
    Some or all expressions may not have rendered properly,
    because REDUCE returned the following error:<br/><pre>%s</pre></font>"""

    reConsts = re.MULTILINE+re.DOTALL
    reduceInPattern = re.compile(
      r'[ \t]*(?<!!)\\begin{reduce}\s*(.*?)\s*\\end{reduce}|'
      r'(?<!!)\\reduce{(.*?)}',reConsts)
    reduceOutPattern = re.compile(
      r'\s*\\begin{displaymath}(.*?)\s*\\end{displaymath}\s*|' #1
      r'\s*\$\$(.*?)\s*\$\$\s*|'   #2
      r'\s*<math>(.*?)</math>|' #3
      r'\s*((?:.(?!\s*<math>)(?!\s*\$\$)(?!\s*\\begin{displaymath}))*.)',
        reConsts)

    def htmlMarkup(code):
        newcode = re.compile(r'^\s+',reConsts).sub(r'',code)
        newcode = re.compile(r'\n\s*\n+',reConsts).sub(r'\n',newcode)
        return re.sub(r'([&<>\$\*\\_])',
               lambda x: { '&':'&amp;',
                           '<':'&lt;',
                           '>':'&gt;',
                           '$':'&#36;',
                            '*':'&#42;',
                           '\\':'&#92;',
                           '_':'&#95;' }[x.group(1)],newcode)

    def translateOutput(N):  
        if N.group(1): # \begin{displaymath}
            return '\\begin{equation}%s\\end{equation}\n'% N.group(1)
        if N.group(2): # $$
            return '$$%s\n$$\n'% N.group(2)
        if N.group(3): # <math>ML just pass it thru
            return '<math xmlns="http://www.w3.org/1998/Math/MathML">%s</math>\n'% N.group(3)
        if N.group(4): # Command
	    r = htmlMarkup(N.group(4))
	    if r:
               return '''<table id="reducecode" width="100%%"><tr>
	         <td><pre>%s</pre></td><td id="reducelabel" valign="top" align="right">reduce</td>
		 </tr></table>\n'''%r
        return ''
 
    def formatOutput(x):
        newCode = reduceOutPattern.sub(translateOutput,x)
        return newCode

    reduceCodeIn = map(lambda x: x[0] or x[1],reduceInPattern.findall(body))
    (reduceCodeOut,errors) = renderReduce(reduceCodeIn)
    if not errors:
        newCodeList = map(formatOutput,reduceCodeOut)
        body = reduceInPattern.sub(lambda x:len(newCodeList) and newCodeList.pop(0) or 'Reduce output parse error!\n',body)
    else:
        body = "<pre>" + body + "</pre>" + errorMessage %(errors)
    return body
