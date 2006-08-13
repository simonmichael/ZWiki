
"""
ReplaceInlineHTML.py v. 0.2.4
  Replace various LaTeX commands with HTML
"""

import re

def replaceInlineHTML(body):
    reConsts = re.MULTILINE+re.DOTALL
    HTMLOutPattern = re.compile(
       r'\{\\tt\s+(.*?)\}|'     #1
        '\{\\bf\s+(.*?)\}|'     #2
        '\\section\{(.*?)\}|'   #3
        '\\subsection\{.*?\}|'  #4
        '\{\\it\s+(.*?)\}',     #5
    reConsts)
    def translateOutput(N):  
        if N.group(1): # \tt
            return '<code>%s</code>'%N.group(1)
        if N.group(2): # \bf
            return  '<b>%s</b>'%N.group(2)
        if N.group(3): # \section
            return  '<h2>%s</h2>'%N.group(3)
        if N.group(4): # \subsection
            return  '<h3>%s</h3>'%N.group(4)
        if N.group(5): # \it
            return '<i>%s</i>'%N.group(5)
        return ''

    return HTMLOutPattern.sub(translateOutput,body)