
"""
ReplaceInlineMaxima.py v. 0.2.3
  Replace Axiom command \\begin{maxima} \\end{maxima} blocks with LaTeX
"""

import re
from string import join,replace

n=1

def replaceInlineMaxima(body):
    from maximaWrapper import renderMaxima
    errorMessage = """\n<hr/><font size="-1" color="red">
    Some or all expressions may not have rendered properly,
    because Maxima returned the following error:<br/><pre>%s</pre></font>"""

    reConsts = re.MULTILINE+re.DOTALL
    maximaInPattern = re.compile(
        r'[ \t]*(?<!!)\\begin *{maxima}\s*(.*?)\s*\\end *{maxima}', #0
        reConsts)
    maximaOutPattern = re.compile(
        #r'<latex>.*?black\}(.*?)</latex>'              #1 LaTeX
        r'<latex>\\mbox{\\tt\\red\(\\mathrm{\\%(i\d+)}\) \\black}(.*?)</latex>|'   #1 #2 Input
        r'<latex>\\mbox{\\tt\\red\(\\mathrm{\\%(o\d+)}\) \\black}(.*?)</latex>|'   #3 #4 Output
        r'stdin:((?:.(?!<latex>))*.)',  #5 Other stuff
        reConsts)

    def htmlMarkup(code):
        newcode = code
        newcode = re.compile(r'\n\s*\n+',reConsts).sub(r'\n',newcode)
        return re.sub(r'([&<>\$\*_\'\\\"])',
               lambda x: { '&':'&amp;',
                           '<':'&lt;',
                           '>':'&gt;',
                           '$':'&#36;',
                           '*':'&#42;',
                           '#':'&#35;',
                           '\\':'&#92;',
                           '[':'![',
                           '\'':'&apos;',
                           '"':'&quot;',
                           '_':'&#95;'
                         }[x.group(1)],newcode)

    def linebreak(x):
        from texbreaker import texbreak, cvar # Robert Sutor's C program
        texbreak(replace(x,'\n',' '))
        return cvar.bufout
    
    def translateOutput(N):  
        global n

        if N.group(1):
            return '<div id="maximainput"><div id="maximalabel" align="right">maxima</div><table width="100%%"><tr><td id="label" width="10%%">(%%%s)</td><td id="equationi">\\begin{equation*}\n%s\n\\end{equation*}\n</td></tr></table></div>\n'%\
              (N.group(1),N.group(2).strip())
        if N.group(3):
            return '<div id="maximaoutput"><table width="100%%"><tr><td id="label" width="10%%">(%%%s)</td><td id="equation">\\begin{equation}\n%s\n\\end{equation}\n</td></tr></table></div>'%\
              (N.group(3),N.group(4).strip())
        if N.group(5):
            return '<div id="maximacode"><pre><div id="maximalabel" align="right">maxima</div>%s</pre></div>\n'%htmlMarkup(N.group(5))
        return 'Pattern Error'

    def formatOutput(x):
        global n
        newCode = maximaOutPattern.sub(translateOutput,x)
        return newCode

    maximaCodeIn = maximaInPattern.findall(body)
    (maximaCodeOut,errors) = renderMaxima(maximaCodeIn)
    if not errors:
        newCodeList = map(formatOutput,maximaCodeOut)
        #newCodeList = maximaCodeOut
        body = maximaInPattern.sub(lambda x:len(newCodeList) and newCodeList.pop(0) or '<font color="red">Maxima output parse error!</font>\n',body)
    else:
        body = "<pre>" + body + "</pre>" + errorMessage %(errors)
    return body
