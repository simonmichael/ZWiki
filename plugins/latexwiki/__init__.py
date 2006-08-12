"""
LatexWiki - LaTeX-supporting page types for ZWiki.

Sean Bowman, Joe Koberg, Bob McElrath, Simon Michael, ...

This is a minimal version, updated for Zwiki 0.52 or thereabouts.
See ChangeLog for more notes.
"""

# install the new Zwiki page type
import stxlatex

# backwards compatibility for old zodb objects
ZwikiLatexPageType     = stxlatex.PageTypeStxLatex
ZwikiHtmlLatexPageType = stxlatex.PageTypeStxLatex
ZwikiItexPageType      = stxlatex.PageTypeStxLatex

# install the default latex wiki
# not yet
