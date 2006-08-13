"""
Replace Latex math mode/\\begin{}\\end{} blocks with html img tag
after rendering

$Id: ReplaceInlineLatex.py,v 1.11 2001/09/07 14:21:16 rsbowman Exp $

TODO:
    test a table/array
    use \\ref{shit} to make reference to equations.  Convert \\ref{shit} to the
    appropriate (number): add negative match to latexPattern for \\ref, do a
        s/// after generating an equation with a \\label.
    Separate vertical alignment characters & into a new
        \\end{equation}\\begin{equation} and then render the separate images in
        a table to acheive vertical alignment.

"""

import re, os
#from collections import deque
from DocumentTemplate.html_quote import html_quote
from util import fileNameFor, imagesPath, workingDir, getPngSize
from string import strip, join, replace
from latexWrapper import runCommand, log
from ReplaceInlineAxiom import replaceInlineAxiom
from ReplaceInlineReduce import replaceInlineReduce
from ReplaceInlineMaxima import replaceInlineMaxima
from ReplaceInlineHTML import replaceInlineHTML

# This will fail on nested blocks \begin{array} \begin{array}...\end{array} \end{array} 
# It is necessary for this to be all one regex (unfortunately) so that we do
# not pick up equations inside \begin{latex}...\end{latex}, rather only the
# outer delimiters.
#latexPattern = r'(?<!\\)(?:\\\\)*(!?\$(?:[^\$\\]|\\[^\$\\]|\\\$|\\\\)*?\$|!?\\\((?:[^\\]|\\[^\)]|\\\\)*?\\\)|!?(?:\\begin{ *([^}]+?) *}.*?\\end{ *\2 *}|\\\[(?:[^\\]|\\[^\]]|\\\\)*?\\\]))'
#latexPattern = r'(?<!\\)(?:\\\\)*(!?\$(?:[^\$\\]|\\[^\$\\]|\\\$|\\\\)*?\$|!?\\\((?:[^\\]|\\[^\)]|\\\\)*?\\\)|!?(?:[ \t]*\\begin{ *([^}]+?) *}.*?\\end{ *\2 *}[ \t]*\n?|\\\[(?:[^\\]|\\[^\]]|\\\\)*?\\\]))'
#   r'!?(?<!\$)\$(?:[^\$\\\n ]|\\.)*?\$(?!\$)|'
latexPattern = re.compile(
  r'(?<!\\)(?:\\\\)*(!?\$\$(?:[^\$\\]|\\.)*?\$\$|'
  r'!?\$(?:[^\$\\\n]|\\.)*?\$|'
  r'!?\\\((?:[^\\]|\\[^\)]|\\\\)*?\\\)|'
  r'!?(?:\\begin{ *([^}]+?) *}.*?\\end{ *\2 *}|'
  r'\\\[(?:[^\\]|\\[^\]]|\\\\)*?\\\]))',
  re.DOTALL)

#latexRemoveDelim = r'^(?:(\$\$|\$(?!\$))|\\\(|\\begin{[^}]*}|\\\[)(.*?)(?:\\\]|\\end{[^}]*}|\\\)|\1)$'

errorMessage = """\n<hr/><font size="-1" color="red">
Some or all expressions may not have rendered properly,
because Latex returned the following error:<br/><pre>%s</pre></font>"""

def findLatexCode(text):
    codeList = map(lambda x: x[0], latexPattern.findall(text))
    return codeList

def replaceInlineLatex(body, charheightpx, alignfudge, resfudge, latexTemplate=None):
    from latexWrapper import renderNonexistingImages
    global savePre
    savePre=[]
    reConsts = re.DOTALL+re.MULTILINE

    def hidePre(x):
        global savePre
        savePre.append(x.group(0))
        return '<pre></pre>'

    def restorePre(x):
        global savePre
        first,savePre = savePre[0],savePre[1:]
        return first

    renumbered   = re.compile(r'[ \t]*\\begin{ *(math|equation|eqnarray) *}')
    reunnumbered = re.compile(r'[ \t]*(\\begin{ *((math|equation|eqnarray)\*|table|tabular|displaymath|array|latex) *}|\$\$)')
#    renumbered   = re.compile(r'\\begin{ *(math|equation|eqnarray) *}')
#    reunnumbered = re.compile(r'[ \t]*(\\begin{ *((math|equation|eqnarray)\*|table|tabular|displaymath|array|latex) *}|\\\[)')
    body = replaceInlineHTML(body) # do extended LaTeX to HTML conversions
    body = replaceInlineAxiom(body) # execute Axiom commands
    body = replaceInlineMaxima(body) # execute Maxima commands
    body = replaceInlineReduce(body) # execute Reduce commands
    # body = re.sub(r'<pre(?: .*?)?>.*?</pre>',hidePre,body,reConsts)
    latexCodeList = findLatexCode(body) # find the rest of the LaTeX
    newlatexCodeList = []
    eqnum = 0
    for code in latexCodeList:
        if code[0]=='!': 
# We need to identify if we're inside a '' block or an example:: block here.
            newcode = re.compile('^!', re.MULTILINE).sub('', code)
            # change the dollar sign so that the replace below does not hit
            # this code again (in the case of the same code appearing twice,
            # once escaped, once not)
            #newcode = re.compile('\$', re.MULTILINE).sub('&#36;', newcode, 2)
            # prevent stx from mangling asterisks
            #newcode = re.compile('\*', re.MULTILINE).sub('&#42;', newcode) 
            # and this will hide \(\), \[\], \begin...\end, including any
            # equations that may be hiding inside a \begin{latex}..\end{latex}
            newcode = re.compile(r'\\\[', re.MULTILINE).sub('\\![', newcode)
            #newcode = re.compile(r'\\', re.MULTILINE).sub('&#92;', newcode)
            body = replace(body, code, newcode, 1)
            continue
        else:
            newlatexCodeList.append(code)
        oldcode = code
        renummatch = renumbered.match(code)
        if renummatch:
            eqnum = eqnum + 1
            code = renumbered.sub('\\\\begin{\\1*}\n\\label{eq%d}' %(eqnum), code, 1)
            kind = renummatch.group(1)
            code = re.compile('\\\\end{ *%s *}' %(kind)).sub('\\\\end{%s*}' %(kind), code, 1)
            code = renumbered.sub('\\\\begin{\\1*}\n\\label{eq%d}' %(eqnum), code, 1)
# FIXME we really shouldn't do this...it will recreate block equations with different numbers.
            newlatexCodeList[newlatexCodeList.index(oldcode)] = code
# FIXME This will also replace any escaped code :(
            body = replace(body, oldcode, code, 1)
    errors = renderNonexistingImages(newlatexCodeList, charheightpx, alignfudge, resfudge,
                                     latexTemplate=latexTemplate)
    
    if not errors:
        for code in newlatexCodeList:
            labelmatch = re.compile('\\\\label{eq(\\d+)}').search(code, 1)
            commentedcode = re.compile('^', re.MULTILINE).sub('!', html_quote(code))
# "--" inside a comment screws up browsers.  But in LaTeX math mode "--" and "- -" are equivalent.
            commentedcode = re.compile('--', re.MULTILINE).sub('- -', commentedcode)
            if labelmatch:
                eqnum = labelmatch.group(1)
                imageTag = '<a name="eq%s">' %(eqnum)                           \
                    + '<table width="95%"><tr><td align="center" width="95%">'                  \
                    + getImageFor(code, charheightpx)                                         \
                    + '</td><td width="5%%" align="right">(%s)</td></tr></table></a>' %(eqnum)

#                    + '\n<!--\n' + commentedcode + '\n-->\n'                 \
            elif reunnumbered.match(code):
                imageTag = '<a name="unnumbered">'\
                    + '<table width="95%"><tr><td align="center" width="95%">'             \
                    + getImageFor(code, charheightpx)                                         \
                    + '</td><td width="5%" align="right">&nbsp;</td></tr></table></a>'
#                    + '\n<!--\n' + commentedcode + '\n-->\n'                 \
            else:
                imageTag = getImageFor(code, charheightpx)
            body = replace(body, code, imageTag, 1)

# We try to match the > and < (or ^/$) from the preceeding and trailing tags,
# so as not to catch the alt="..." from a latex equation
# FIXME this is slow.  Use something like perl's m/\G/g to iterate over (n)
        for i in range(1,int(eqnum)+1):
            body = re.compile(r'((?:>|^)(?:[^<]*\s|))\( *(?:[Ee][Qq]\.)?\s*(%d) *\)([^>]*(?:<|$))' %(i)).sub(r'\1<a href="#eq\2">(\2)</a>\3', body)

    else:
        body = '<pre>' + body + '</pre>' + errorMessage %(errors)

    # Handle escaping of latex
    body = re.compile(r'(?<!\\)((?:\\\\)*)\\\$', re.MULTILINE).sub(r'\1$', body)
    body = re.compile(r'\\\\', re.MULTILINE).sub(r'\\', body)
    # body = re.sub(r'<pre></pre>',restorePre,body,reConsts)
    return body

def getImageFor(latexCode, charheightpx):    
    preamble, postamble = '', ''
    width, height = '', '' 
    imageFile = fileNameFor(latexCode, charheightpx, '.png')
    imageUrl = imagesPath + imageFile
    width, height = getPngSize(os.path.join(workingDir, imageFile))
    #src = html_quote(re.match(latexRemoveDelim, latexCode, re.MULTILINE|re.DOTALL). group(2))
    src = 'LatexWiki Image'
    return '%s<img alt="%s" class="equation" src="%s" width="%s" height="%s"/>%s' %(preamble,
                                                            src,
                                                            imageUrl,
                                                            width,
                                                            height,
                                                            postamble)
    #return '%s<img class="equation" src="%s" width="%s" height="%s"/>%s' %(preamble,
    #                                                        imageUrl,
    #                                                        width,
    #                                                        height,
    #                                                        postamble)
