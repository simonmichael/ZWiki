# Unit tests for ZWiki. These have been through a few contortions.
# Working on simplifying them and conforming to the latest One True Way
# (running at the command line via testrunner.py). 
#
# Old notes:
#
#  how to do authentication/permissions-related testing ?
#
#  test functionality of all the different page types, with no, good &
#  bad dtml
#
#  test edit's various cases
#
#  test leading & trailing newline preservation
#
#  test initial http-like-header: preservation
#
#  test whether stx heading on first line works
#
#  test all the various kinds of links - mailto, http, wikiname,
#  remotewikilink, stx, combinations..
#
#  test handling of large cookies, empty cookies, missing cookies by
#  UserOptions, editform, standard_wiki_header...
#
#  test rendering without dtml methods and with various other versions
#  of the methods
#
#  test with other zope versions (at least product startup). Test
#  with/without ZWikiWebs; ZUnit; doctest; other ZWiki versions; other
#  related products
#
#  test zwiki_base,page_url with & without a SiteRoot
#
#  test permissions
#
#  the prerelease checklist on http://zwiki.org/ZWikiWebs
#
#  check all version nos. are correct (special prerelease test ?)
#
#  what's the best way to handle sometimes-applicable tests - like the
#  above, or testing virtual hosting only if SiteAccess is found 
#
#  tests that would catch eg the deepappend bug that broke page
#  creation from a top-level page, eg: visit both
#  TestPage/editform?page=NewPage and
#  TestPage/SubPage/editform?page=NewPage, in a basic wiki (simple
#  title) and a zwikidotorg wiki (with show_hierarchy enabled)
#  (SubPage should be a child of TestPage, add this to setup)
