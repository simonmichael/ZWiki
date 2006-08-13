
"""
ReplaceInlineAxiom.py v. 0.2.3
  Replace Axiom command \\begin{axiom} \\end{axiom} blocks with LaTeX
"""

import re
from string import join,replace

n=1

def replaceInlineAxiom(body):
    from axiomWrapper import renderAxiom
    errorMessage = """\n<hr/><font size="-1" color="red">
    Some or all expressions may not have rendered properly,
    because Axiom returned the following error:<br/><pre>%s</pre></font>"""

    reConsts = re.MULTILINE+re.DOTALL
    axiomInPattern = re.compile(
        r'[ \t]*(?<!!)\\begin *{axiom}\s*(.*?)\s*\\end *{axiom}|' #0
        r'(?<!!)\\spadcommand{(.*?)}|'                            #1
        r'[ \t]*(?<!!)(\\begin *{spad}\s*.*?\s*\\end *{spad})|'   #2
        r'[ \t]*(?<!!)(\\begin *{aldor}\s*.*?\s*\\end *{aldor})|' #3
        r'[ \t]*(?<!!)(\\begin *{boot}\s*.*?\s*\\end *{boot})|'   #4
        r'[ \t]*(?<!!)(\\begin *{lisp}\s*.*?\s*\\end *{lisp})',   #5
        reConsts)
    axiomOutPattern = re.compile(
        r'\s*\n\$\$(.*?)\s*\n\$\$|'      #1
        r'\s*(Type: [^\n]*)|'            #2
        r'\s*Loading ([^ ]*?)\.(?=\s)|'  #3
        r'\s*Loading ([^ ]*?) for (package|domain|category)\s+(.*?)\s|' # 4,5,6
        r'\s*((?:.(?!\s*Type:)(?!\s*\n\$\$)(?!\s*Loading)(?!\s*Compiling))*.)', #7
        reConsts)
    requires = dict({'package':[],'domain':[],'category':[]})

    def htmlMarkup(code):
        newcode = code
#       newcode = re.compile(r'\n',reConsts).sub(r' \n',newcode)
        newcode = re.compile(r'\n\s*\n+',reConsts).sub(r'\n',newcode)
        return re.sub(r'([&<>\$\*_\'\\])',
#                     r'([&<>\$\*\\_])',
               lambda x: { '&':'&amp;',
                           '<':'&lt;',
                           '>':'&gt;',
                           '$':'&#36;',
                           '*':'&#42;',
                           '#':'&#35;',
                           '\\':'&#92;',
                           '[':'![',
                           '\'':'&apos;',
                           '_':'&#95;'
                         }[x.group(1)],newcode)

    def fixLoadingInTex(N):
        if N.group(4): # Load WikiNames
            requires[N.group(5)].append('['+N.group(6)+']')
            return '' # We list them later
        else:
            return N.group(1) or N.group(2) or N.group(3) or N.group(7)

    def fixEmbedded(x):
        return axiomOutPattern.sub(fixLoadingInTex,x)

    def linebreak(x):
        # XXX can't build texbreaker yet
        return x 
        #from texbreaker import texbreak, cvar # Robert Sutor's C program
        #texbreak(replace(x,'\n',' '))
        #return cvar.bufout
    
    def translateOutput(N):  
        global n
        if N.group(1): # Equation
            return '\\begin{equation}%s\\end{equation}\n'% \
                linebreak(re.sub(r'\\leqno\(.*?\)',r'',fixEmbedded(N.group(1))))
        if N.group(2): # Type
            return '<div align="right">%s</div>\n'%N.group(2)
        if N.group(3): # Autoload messages
            return '' # Ignore them
        if N.group(4): # Load WikiNames
            requires[N.group(5)].append({'category':'[Cat]:',
                                         'domain':'[Dom]:',
                                         'package':'[Pac]:'}[N.group(5)]+
                                        N.group(6))
            return '' # We list them later
        if N.group(7):
            if re.match(r'^\s*Compiling',N.group(7)): # compiler output
                n=n+1
                return '<div id="axiomtext"><div id="axiomlabel" title="Expand +/- Collapse folded text" align="right" onClick="expandcontent(this, this.nextSibling.id)" style="cursor:hand; cursor:pointer"><span class="showstate"></span>axiom</div><pre id="sc%d" class="switchcontent">%s</pre></div>\n'%(n,htmlMarkup(N.group(7)))
            else: # command
                return '<div id="axiomcode"><pre><div id="axiomlabel" align="right">axiom</div>%s</pre></div>\n'%htmlMarkup(N.group(7))
        return 'Pattern Error'

    def formatOutput(x):
        global n
        requires['package'] = []
        requires['domain'] = []
        requires['category'] = []
        if   re.match(r'^\s*<spad>\n(.*?)</spad>\n(.*)$',x,reConsts):
            m = re.match(r'^\s*<spad>\n(.*?)</spad>\n(.*)$',x,reConsts)
            n=n+1
            newCode = '''<div id="axiomcode"><pre><div id="axiomlabel" align="right">spad</div>%s</pre></div>
<div id="axiomtext"><div id="axiomlabel" title="Expand +/- Collapse folded text"align="right" onClick="expandcontent(this, this.nextSibling.id)" style="cursor:hand; cursor:pointer"><span class="showstate"></span>spad</div><div id="sc%d" class="switchcontent"><pre>%s</pre></div></div>
'''%(htmlMarkup(m.group(1)),n,htmlMarkup(m.group(2)))
        elif re.match(r'^\s*<boot>\n(.*?)</boot>\n(.*)$',x,reConsts):
            m = re.match(r'^\s*<boot>\n(.*?)</boot>\n(.*)$',x,reConsts)
            n=n+1
            newCode = '''<div id="axiomcode"><pre><div id="axiomlabel" align="right">boot</div>%s</pre></div>
<div id="axiomtext"><div id="axiomlabel" title="Expand +/- Collapse folded text"align="right" onClick="expandcontent(this, this.nextSibling.id)" style="cursor:hand; cursor:pointer"><span class="showstate"></span>boot</div><div id="sc%d" class="switchcontent"><pre>%s</pre></div></div>
'''%(htmlMarkup(m.group(1)),n,htmlMarkup(m.group(2)))
        elif re.match(r'^\s*<lisp>\n(.*?)</lisp>\n(.*)$',x,reConsts):
            m = re.match(r'^\s*<lisp>\n(.*?)</lisp>\n(.*)$',x,reConsts)
            n=n+1
            newCode = '''<div id="axiomcode"><pre><div id="axiomlabel" align="right">lisp</div>%s</pre></div>
<div id="axiomtext"><div id="axiomlabel" title="Expand +/- Collapse folded text" align="right" onClick="expandcontent(this, this.nextSibling.id)" style="cursor:hand; cursor:pointer"><span class="showstate"></span>lisp</div><div id="sc%d" class="switchcontent"><pre>%s</pre></div></div>
'''%(htmlMarkup(m.group(1)),n,htmlMarkup(m.group(2)))
        elif re.match(r'^\s*<aldor>\n(.*?)</aldor>\n(.*)$',x,reConsts):
            m = re.match(r'^\s*<aldor>\n(.*?)</aldor>\n(.*)$',x,reConsts)
            n=n+1
            newCode = '''<div id="axiomcode"><pre><div id="axiomlabel" align="right">aldor</div>%s</pre></div>
<div id="axiomtext"><div id="axiomlabel" title="Expand +/- Collapse folded text" align="right" onClick="expandcontent(this, this.nextSibling.id)" style="cursor:hand; cursor:pointer"><span class="showstate"></span>aldor</div><div id="sc%d" class="switchcontent"><pre>%s</pre></div></div>
'''%(htmlMarkup(m.group(1)),n,htmlMarkup(m.group(2)))
        else:
            newCode = axiomOutPattern.sub(translateOutput,x)
 
        for module,names in requires.iteritems():
          if names:
              names.sort()
              newCode = newCode + '\n<div><small>%s: %s</small></div>'%(module,join(names))
        return newCode

    axiomCodeIn = map(lambda x: x[0] or x[1] or x[2] or x[3] or x[4] or x[5],
        axiomInPattern.findall(body))
    (axiomCodeOut,errors) = renderAxiom(axiomCodeIn)
    if not errors:
        newCodeList = map(formatOutput,axiomCodeOut)
        body = axiomInPattern.sub(lambda x:len(newCodeList) and newCodeList.pop(0) or '<font color="red">Axiom output parse error!</font>\n',body)
    else:
        body = "<pre>" + body + "</pre>" + errorMessage %(errors)
    return body
