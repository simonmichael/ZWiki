#===================================================================
#!/usr/bin/env python
# File:    TextFormatter.py
# Author:  Hamish B Lawson
# Date:    19/11/1999
# from http://www.faqts.com/knowledge_base/view.phtml/aid/4517
"""
Here is TextFormatter, a simple module for formatting text into
columns of specified widths. It does multiline wrapping and supports
left, center and right alignment.

SKWM made filling & padding optional, tweaked some edge cases
"""

import string

left  = 0
center = centre = 1
right  = 2

class TextFormatter:

    """
    Formats text into columns.

    Constructor takes a list of dictionaries that each specify the
    properties for a column. Dictionary entries can be:

       width         the width within which the text will be wrapped
       alignment     left|center|right
       margin        amount of space to prefix in front of column

    The compose() method takes a list of strings and returns a formatted
    string consisting of each string wrapped within its respective column.

    Example:

        formatter = TextFormatter(
            (
                {'width': 10},
                {'width': 12, 'margin': 4},
                {'width': 20, 'margin': 8, 'alignment': right},
            )
        )

        print formatter.compose(
            (
                "A rather short paragraph",
                "Here is a paragraph containing a veryveryverylongwordindeed.",
                "And now for something on the right-hand side.",
            )
        )

    gives:

        A rather      Here is a                    And now for
        short         paragraph               something on the
        paragraph     containing a            right-hand side.
                      veryveryvery
                      longwordinde
                      ed.

    """
    class Column:

        def __init__(self, width=75, alignment=left, margin=0, fill=1, pad=1):
            self.width = width
            self.alignment = alignment
            self.margin = margin
            self.fill = fill
            self.pad = pad
            self.lines = []

        def align(self, line):
            if self.alignment == center:
                return string.center(line, self.width)
            elif self.alignment == right:
                return string.rjust(line, self.width)
            else:
                if self.pad:
                    return string.ljust(line, self.width)
                else:
                    return line

        def wrap(self, text):
            self.lines = []
            words = []
            if self.fill:               # SKWM
                for word in string.split(text):
                    if word <= self.width:  # don't understand this
                        words.append(word)
                    else:
                        for i in range(0, len(word), self.width):
                            words.append(word[i:i+self.width])
            else:
                for line in string.split(text,'\n'):
                    for word in string.split(line):
                        for i in range(0, len(word), self.width):
                            words.append(word[i:i+self.width])
                    words.append('\n')
                if words[-1] == '\n': words.pop()
                
            if words:
                current = words.pop(0)
                for word in words:
                    increment = 1 + len(word)
                    if word == '\n':
                        self.lines.append(self.align(current))
                        current = ''
                    elif len(current) + increment > self.width:
                        self.lines.append(self.align(current))
                        current = word
                    else:
                        if current:
                            current = current + ' ' + word
                        else:
                            current = word
                if current: self.lines.append(self.align(current))

        def getline(self, index):
            if index < len(self.lines):
                return ' '*self.margin + self.lines[index]
            else:
                if self.pad:
                    return ' ' * (self.margin + self.width)
                else:
                    return ''

        def numlines(self):
            return len(self.lines)

    def __init__(self, colspeclist):
        self.columns = []
        for colspec in colspeclist:
            self.columns.append(apply(TextFormatter.Column, (), colspec))

    def compose(self, textlist):
        numlines = 0
        textlist = list(textlist)
        if len(textlist) != len(self.columns):
            raise IndexError, "Number of text items does not match columns"
        for text, column in map(None, textlist, self.columns):
            column.wrap(text)
            numlines = max(numlines, column.numlines())
        complines = [''] * numlines
        for ln in range(numlines):
            for column in self.columns:
                complines[ln] = complines[ln] + column.getline(ln)
        #return string.join(complines, '\n') + '\n'
        return string.join(complines, '\n')


def test():
    formatter = TextFormatter(
        (
            {'width': 10},
            {'width': 12, 'margin': 4},
            {'width': 20, 'margin': 8, 'alignment': right},
        )
    )

    print formatter.compose(
        (
            "A rather short paragraph",
            "Here is a paragraph containing a veryveryverylongwordindeed.",
            "And now for something on the right-hand side.",
        )
    )

if __name__ == '__main__':
    test()
