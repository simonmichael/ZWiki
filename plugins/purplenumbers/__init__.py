"""
Purple Numbers support for zwiki pages.

Based on initial implementation by mike@nthwave.net.

"nid" is short for Node Identifier. A nid identifies a block of content.
"""

import os, sys, re, string

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Products.ZWiki.plugins import registerPlugin
from Products.ZWiki.Defaults import registerPageMetaData
from Products.ZWiki.Regexps import fromlineexpr, nidexpr

purplestyle = """
a.nid {
font-family: "Helvetica", "Arial", sans-serif;
font-style: normal;
font-weight: bold;
font-size: x-small;
text-decoration: none;
color: #C8A8FF;
}
"""

class PurpleNumbersSupport:
    """
    Mix-in class to provide (most of the) support for Purple Numbers
    (automatically generated, persistent, fine-grained link targets).
    """
    security = ClassSecurityInfo()

    security.declarePublic('usingPurpleNumbers')
    def usingPurpleNumbers(self):
        return getattr(self,'use_purple_numbers',0) and 1

    security.declarePublic('addPurpleNumbers')
    def addPurpleNumbersTo(self,t,page):
        """
        Add purple numbers (nids) to text as needed, in the context of page.

        A new NID is inserted for each heading, paragraph and list item which
        does not already have one.
        """
        # put purple numbers knowledge with page types or page types
        # knowledge here ? the first
        return self.pageType().addPurpleNumbersTo(page,t)
            
    security.declarePublic('textWithoutPurpleNumbers')
    def textWithoutPurpleNumbers(self):
        return re.sub(nidexpr,'',self.text())

    security.declarePublic('renderPurpleNumbersIn')
    def renderPurpleNumbersIn(self, text):
        """Convert purple numbers (NIDs) in some HTML text to links & targets.

        The text is assumed to be simple HTML, eg as output by STX or RST,
        with balanced H, P and LI tags containing NIDs in source form. We
        don't parse the SGML, but stick with tradition and do some dumb
        regexp stuff.
        """
        chunks = re.split(r'(?is)(<(H|P|LI).*?</\2[^>]*?>)',text)
        # compensate for split's including the second group.. should be safe enough
        chunks = filter(lambda x:not re.match('(?i)(H|P|LI)',x), chunks)
        for i in range(len(chunks)):
            c = chunks[i]
            m = re.search(nidexpr,c)
            if m:
                start, end, nid = m.start(), m.end(), m.group('nid')
                chunks[i] = self.renderPurpleTarget(nid) + \
                            c[:start] + \
                            self.renderPurpleLink(nid) + \
                            c[end:]
        return string.join(chunks,'')

    security.declarePublic('renderPurpleTarget')
    def renderPurpleTarget(self, purpleNumberString):
        return '<a id="nid%s" name="nid%s"></a>' % (purpleNumberString,purpleNumberString)

    security.declarePublic('renderPurpleLink')
    def renderPurpleLink(self, purpleNumberString):
        return '&nbsp;&nbsp;<a href="%s#nid%s" class="nid" style="font-family:Helvetica,Arial,sans-serif;font-weight:bold;font-size:x-small;text-decoration:none;color:#C8A8FF">(%s)</a>'\
               % (self.page_url(),purpleNumberString,purpleNumberString)

InitializeClass(PurpleNumbersSupport)
registerPlugin(PurpleNumbersSupport)

# mike's code
#
#        addPurpleToggle == 0|1 set default for new folders. 
#                Turns off|on Purple Numbers on the wiki folder. 
#                Setting an existing folder property (in the ZMI) to 0 will
#                leave existing nids embedded in the page source, but new
#                nids will no longer be added and existing nids will not be
#                displayed.
#
#        displayPurpleToggle == 0|1 set default display of Purple Numbers for new folders. 
#                Setting an existing folder property (in the ZMI) to 0 will
#                turn off display of existing nids.
#
#        purpleNumberDataType
#                can be the name of a method that accepts a nid as integer
#                (the lastPurpleID) and returns a string representation of
#                the nid. e.g. purpleNumberDataBase36 and
#                purpleNumberDataBase62
#
#        nidMarker is a pair of characters which mark the begin and end of a nid. 
#                It may be whatever you like, but in ZWiki, the square
#                brackets "[" & "]" cause problems.
#
#TO DO
#        ensure the lastPurpleId is safe from concurrent requests

# default for new folders. 0|1 turn off|on Purple Number embedding and
# display for new folder
addPurpleToggle = 1
# default for new folders. 0|1 turn off|on Purple Number display. ignored
# when addPurpleToggle == 0
displayPurpleToggle = 1 
nidMarker = ('{', '}')
# NOTE: ?P<stx> in the regex below contains all the StructuredText
# markers.  Different StructuredText rules require changes here.
stx_re=re.compile("^(?P<indent>\s*)(?P<stx>[-\*o]|(\d+\.? ?))(?P<content>.*)")
findNID_re = re.compile(nidMarker[0] +"nid (?P<nid>.+)"+ nidMarker[1])
#findIndent_re = re.compile("^(?P<indent>\s*)")

def add_purple_numbers_to(text, page):
    """
    Add Purple Number NIDs to source text in the context of page.

    Assumes text is structured text right now.
    The various page types call this.
    """
    p = PurpleProperties(page)
    #if not p.getAddPurpleToggle(): return text
    #text = string.replace(text, "\r\n", "\n")
    #text = string.replace(text, "\r", "\n")
    text = string.split(text, "\n")
    ct = len(text)
    in_message_header = 0
    for i in range(ct):
        if not string.strip(text[i]): continue #this is a blank line
        if findNID_re.search(text[i]): continue # this line already has a nid
        if re.match(fromlineexpr,'\n\n'+text[i]): # SKWM message header, skip nid
            in_message_header = 1 
        elif (i < ct -1) and (not string.strip(text[i +1])): # next line blank
            if in_message_header:
                in_message_header = 0
            elif re.search('::\s*$',text[i]): # SKWM put nid before STX ::
                j = text[i].rfind('::')
                text[i] = text[i][:j] + buildNID(p.getNewPurpleId()) + \
                          text[i][j:]
            else:
                text[i] += buildNID(p.getNewPurpleId())
        elif (i < ct -1) and (string.strip(text[i +1])): # next line not blank
            if stx_re.match(text[i +1]): # next line begins with list-type stx
                text[i] += buildNID(p.getNewPurpleId())
            #else:
            #        mo1 = findIndent_re.match(text[i])
            #        mo2 = findIndent_re.match(text[i +1])
            #        if mo1.group('indent') != mo2.group('indent'): #they have different indents
            #                text[i] += buildNID(p.getNewPurpleId())
        elif (i == ct -1): # the last line is not blank
            text[i] += buildNID(p.getNewPurpleId())
    return string.join(text, os.linesep)

class PurpleProperties:
    """
    Manage a wiki's purple numbers properties.
    """
    def __init__(self, page): 
        self.page = page
        try:
            self.page.folder().lastPurpleId
        except: # we've never touched this folder before
            self.page.folder().lastPurpleId = 0
            self.page.folder().addPurpleToggle = addPurpleToggle
            self.page.folder().displayPurpleToggle = displayPurpleToggle

    def getNewPurpleId(self):
        "Get the lastPurpleId, increment it, return string."
        self.page.folder().lastPurpleId +=1
        return self.page.folder().lastPurpleId

    def getAddPurpleToggle(self):
        return self.page.folder().addPurpleToggle

    def getDisplayPurpleToggle(self):
        return self.page.folder().displayPurpleToggle

def makeBaseNumber(base10, digits):
        """Convert a base10 integer to a base[newBase] number."""
        newBase = len(digits)
        power = 0
        while 1:# find the smallest power of newBase greater than the base10 integer
                power +=1
                if base10 < newBase**power:
                        power -=1 # we want the largest power of newBase smaller than base10
                        break
        nid = ''
        while power >= 0: # pull out large units until base10 is zero
                nid += digits[base10 / newBase** power]
                base10 = base10 % newBase** power
                power -=1
        return nid

def purpleNumberDataInt(n):
        "Display the node id as str(integer)."
        return str(n)

def purpleNumberDataBase36(n):
        "Display the node id as str(base36) e.g. 34A5D [1-90A-Z]."
        digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return makeBaseNumber(n, digits)

def purpleNumberDataBase62(n):
        "Display the node id as str(base62) e.g s4UI [1-90A-Za-z]]."
        digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        return makeBaseNumber(n, digits)

def purpleNumberDataBase10(n):
        "Display the node id as str(base10)."
        digits = "0123456789"
        return makeBaseNumber(n, digits)

purpleNumberDataType = purpleNumberDataBase10

def buildNID(n):
        return ' '+ nidMarker[0] +'nid '+ purpleNumberDataType(n) + nidMarker[1]

