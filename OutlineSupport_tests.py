from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

from Products.ZWiki.Outline import Outline

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

def setupSomePageHierarchy(self):
    self.page.create('RootPage')
    self.wiki.RootPage.reparent(REQUEST=self.request)
    self.wiki.RootPage.create('ChildPage')
    self.wiki.ChildPage.create('GrandChildPage')
    self.page.create('SingletonPage')
    self.wiki.SingletonPage.reparent(REQUEST=self.request)

class Tests(ZwikiTestCase):
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        setupSomePageHierarchy(self)

    def beforeTearDown(self):
        # this usually gets generated.. clear it so next tests
        # will get a fresh one
        self.wiki._delObject('outline')

    def test_wikiOutline(self):
        self.assert_(hasattr(self.wiki,'outline'))
        o = self.page.wikiOutline()
        self.assertEquals(o,self.wiki.outline)
        self.assertEquals(o.nesting(),
                          [['RootPage',
                            ['ChildPage',
                             'GrandChildPage']],
                           'SingletonPage',
                           'TestPage',
                           ])
        # stray empty parents should be ignored
        self.wiki.TestPage.parents = ['']
        self.wiki.ChildPage.parents.append('')
        o = self.page.wikiOutline()
        self.assertEquals(o.nesting(),
                          [['RootPage',
                            ['ChildPage',
                             'GrandChildPage']],
                           'SingletonPage',
                           'TestPage',
                           ])
        self.assertEquals(o.parentmap()['TestPage'],[])
        self.assertEquals(o.parentmap()['ChildPage'],['RootPage'])
        
    def test_context(self):
        self.assertEquals(self.wiki.RootPage.context(),
                          '&nbsp;') # XXX should be as below I think
        self.assertEquals(self.wiki.RootPage.context(with_siblings=1),
                          '<small><ul class="outline expandable">\n <li><a href="http://nohost/test_folder_1_/wiki/RootPage" name="RootPage">RootPage</a> <span id="youarehere"><-- You are here.</span> ...\n </li>\n</ul>\n</small>'
                          )
        self.assertEquals(self.wiki.ChildPage.context(),
                          '<small><ul class="outline expandable">\n <li><a href="http://nohost/test_folder_1_/wiki/RootPage" name="RootPage">RootPage</a>\n<ul class="outline expandable">\n <li><a href="http://nohost/test_folder_1_/wiki/ChildPage" name="ChildPage">ChildPage</a> <span id="youarehere"><-- You are here.</span></li>\n</ul>\n </li>\n</ul>\n</small>'
                          )
        
    def test_reparent(self):
        p = self.wiki.SingletonPage
        self.wiki.RootPage.create('Parent Page')
        self.wiki.RootPage.create('Parent Page 2')
        self.wiki.RootPage.create('Parent Page 3')
        # no args clears parents
        p.parents = ['old']
        p.reparent(REQUEST=self.request)
        self.assertEquals(p.parents,[])
        # invalid page names are stripped
        p.reparent(parents=['nosuchpage'],REQUEST=self.request)
        self.assertEquals(p.parents,[])
        # reparent by id, leaves title in parents
        p.reparent(parents=['ParentPage'],REQUEST=self.request)
        self.assertEquals(p.parents,['Parent Page'])
        # reparent by fuzzy name
        p.reparent(parents=[' Parent page 2..'],REQUEST=self.request)
        self.assertEquals(p.parents,['Parent Page 2'])
        # reparent by freeform name, as string
        p.reparent(parents='Parent Page 3',REQUEST=self.request)
        self.assertEquals(p.parents,['Parent Page 3'])
        # duplicates are removed
        p.reparent(parents=['ParentPage','Parent Page','parent-page'],
                   REQUEST=self.request)
        self.assertEquals(p.parents,['Parent Page'])
        # the wiki outline object is also updated
        self.assertEquals(p.wikiOutline().parents('SingletonPage'),
                          ['Parent Page'])
        p.reparent(parents=['TestPage'],REQUEST=self.request)
        self.assertEquals(p.wikiOutline().parents('SingletonPage'),
                          ['TestPage'])

    def test_offspringIdsAsList(self):
        self.assertEquals(self.wiki.RootPage.offspringIdsAsList(),
                          ['ChildPage','GrandChildPage'])
        self.assertEquals(self.wiki.ChildPage.offspringIdsAsList(),
                          ['GrandChildPage'])
        self.assertEquals(self.wiki.GrandChildPage.offspringIdsAsList(),
                          [])

