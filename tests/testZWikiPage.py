import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

class ZWikiPageTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_excerptAt(self):
        self.page.edit(text='This is a test of the<br />\n excerptAt method,')
        self.assertEquals(self.page.excerptAt('excerptat',size=10,highlight=0),
                          '\n excerptAt ')
        #self.assertEquals(self.page.excerptAt('this*',size=21,highlight=1),
        #                  '<span class="hit">This</span> is a tes')
        #self.assertEquals(self.page.excerptAt('br',size=4),
        #                  'e&lt;<span class="hit">br</span>&gt;\n')
        # XXX temp
        self.assertEquals(self.page.excerptAt('this*',size=21,highlight=1),
                          '<span class="hit" style="background-color:yellow;font-weight:bold;">This</span> is a tes')
        self.assertEquals(self.page.excerptAt('br',size=4),
                          'e&lt;<span class="hit" style="background-color:yellow;font-weight:bold;">br</span> /')
        self.assertEquals(self.page.excerptAt('<br />',size=4,highlight=0),
                          '&lt;br /&gt;')
        self.assertEquals(self.page.excerptAt('nomatch'),'')
        self.assertEquals(self.page.excerptAt(''),'')

    def testWithPartialCatalog(self):
        # a number of things are known to be affected by a partial catalog
        # - usually a standard CMF/plone portal_catalog that wasn't set up
        # for Zwiki, but could also be a catalog that's had some of the
        # zwiki fields removed - eg IssueNo0623.  These seem to boil down
        # to ensuring the brains returned by pages() have all expected
        # fields.
        self.page.setupCatalog()
        self.page.catalog().manage_delColumn('parents')
        brain = self.page.pages()[0]
        self.assert_(hasattr(brain,'parents'))

    def test_canonicalIdFrom(self):
        p = self.page
        self.assertEquals(p.canonicalIdFrom('WikiName'),'WikiName')
        self.assertEquals(p.canonicalIdFrom('ZWikiWikiNames2'),'ZWikiWikiNames2')
        self.assertEquals(p.canonicalIdFrom('a page with !'),'APageWith')
        self.assertEquals(p.canonicalIdFrom('a_page'),'APage')
        self.assertEquals(p.canonicalIdFrom('Test\xc3Page'),'Test_c3Page') # A tilde
        self.assertEquals(p.canonicalIdFrom('\xc3Page'),'X_c3Page')
        self.assertEquals(p.canonicalIdFrom('_c3Page'),'C3Page')

    def test_asAgeString(self):
        #p = self.page
        p = MockZWikiPage().aq_parent.TestPage
        self.assertEqual(p.asAgeString(p.last_edit_time),'some time')

    def test_pageIdsStartingWith(self):
        p = self.page
        p.create('TestPage2')
        self.assertEqual(p.pageIdsStartingWith('Test'),
                         ['TestPage','TestPage2'])

    def test_pageNamesStartingWith(self):
        p = self.page
        p.title = 'Test Page'
        p.create('Test Page 2')
        self.assertEqual(p.pageNamesStartingWith('Test'),
                         ['Test Page','Test Page 2'])

    def test_firstPageIdStartingWith(self):
        p = self.page
        p.create('TestPage2')
        self.assertEqual(p.firstPageIdStartingWith('Test'),'TestPage')

    def test_firstPageNameStartingWith(self):
        p = self.page
        p.title = 'Test Page'
        p.create('Test Page 2')
        self.assertEqual(p.firstPageNameStartingWith('Test'),'Test Page')

    def test_pageWithId(self):
        p = self.page
        self.failIf(p.pageWithId('nosuchid'))
        self.failUnless(p.pageWithId('TestPage'))
        self.failIf(p.pageWithId('testpage'))
        self.failUnless(p.pageWithId('testpage',ignore_case=1))

    def test_pageWithName(self):
        p = self.page
        p.title = 'Test page'
        self.failUnless(p.pageWithName(p.title))

    def test_pageWithFuzzyName(self):
        p = self.page
        p.title = 'Test page'
        self.failUnless(p.pageWithFuzzyName('Test page'))
        self.failUnless(p.pageWithFuzzyName(' Test  page\t'))
        self.failUnless(p.pageWithFuzzyName('TestPage'))
        self.failUnless(p.pageWithFuzzyName('TEST Page'))
        self.failUnless(p.pageWithFuzzyName('Testpage'))
        self.failIf(p.pageWithFuzzyName('test'))
        self.failUnless(p.pageWithFuzzyName('test',allow_partial=1))

    def test_backlinksFor(self):
        p = self.page
        p.title = 'Test Page'
        p.create('PageTwo',text='[Test Page]')
        p.create('PageThree',text='TestPage')
        self.assertEqual(len(p.backlinksFor('Test Page')),2)

    def test_isWikiName(self):
        p = self.page
        self.assert_(p.isWikiName('WikiName'))
        self.assert_(p.isWikiName('WikiName2'))
        self.assert_(p.isWikiName('AWikiName'))
        self.assert_(not p.isWikiName('Wikiname'))
        self.assert_(not p.isWikiName('Wiki2Name'))

    def test_hasAllowedLinkSyntax(self):
        self.assertEquals(self.p.hasAllowedLinkSyntax('WikiName'),1)
        self.p.use_wikiname_links = 0
        self.assertEquals(self.p.hasAllowedLinkSyntax('WikiName'),0)
        self.p.use_wikiname_links = 1
        self.assertEquals(self.p.hasAllowedLinkSyntax('WikiName'),1)
        self.assertEquals(self.p.hasAllowedLinkSyntax('[freeform name]'),1)
        self.p.use_bracket_links = 0
        self.assertEquals(self.p.hasAllowedLinkSyntax('[freeform name]'),0)
        self.p.use_bracket_links = 1
        self.assertEquals(self.p.hasAllowedLinkSyntax('[freeform name]'),1)
        self.assertEquals(self.p.hasAllowedLinkSyntax('[[double brackets]]'),1)
        self.p.use_doublebracket_links = 0
        self.assertEquals(self.p.hasAllowedLinkSyntax('[[double brackets]]'),0)
        self.p.use_doublebracket_links = 1
        self.assertEquals(self.p.hasAllowedLinkSyntax('[[double brackets]]'),1)

    def test_markLinksIn(self):
        self.assertEquals(self.p.markLinksIn('test'),'test')
        self.assertEquals(self.p.markLinksIn('http://url'),
                          '<zwiki>http://url</zwiki>')
        self.assertEquals(
            self.p.markLinksIn(
            'WikiName, [freeform name], [[double brackets]]'),
            '<zwiki>WikiName</zwiki>, <zwiki>[freeform name]</zwiki>, <zwiki>[[double brackets]]</zwiki>')
        self.p.use_wikiname_links = 0
        self.p.use_bracket_links = 0
        self.p.use_doublebracket_links = 0
        self.assertEquals(
            self.p.markLinksIn(
            'WikiName, [freeform name], [[double brackets]]'),
            'WikiName, [freeform name], [[double brackets]]')

    def test_formatWikiname(self):
        self.assertEquals(self.p.formatWikiname('CamelCase'),'CamelCase')
        self.p.folder().space_wikinames = 1
        self.assertEquals(self.p.formatWikiname('CamelCase'),'Camel Case')

    def test_renderLink(self):
        self.assertEquals(
            self.p.renderLink('[unbalanced (]')[-53:],
            'page=unbalanced%20%28" title="create this page">?</a>')
        self.assertEquals(
            self.p.renderLink('http://some.url'),
            '<a href="http://some.url">http://some.url</a>')
        #self.p.folder().space_wikinames = 1
        #self.assertEquals(self.p.renderLink('CamelCase')[:10],'Camel Case')
        
    def test_renderLinksIn(self):
        self.assertEquals(self.p.renderLinksIn('nolink'),'nolink')
        self.assertEquals(self.p.renderLinksIn('http://a.b.c/d'),
                          '<a href="http://a.b.c/d">http://a.b.c/d</a>')
        self.assertEquals(self.p.renderLinksIn('mailto://a@b.c'),
                          '<a href="mailto://a@b.c">mailto://a@b.c</a>')
        #import pdb; pdb.set_trace()
        self.assertEquals(self.p.renderLinksIn('TestPage'),
                          '<a href="http://nohost/test_folder_1_/wiki/TestPage" title="" style="background-color:;">TestPage</a>')
#                          '<a href="/test_folder_1_/wiki/TestPage" title="" style="background-color:;">TestPage</a>')
        self.assertEquals(self.p.renderLinksIn('NewTestPage'),
                          'NewTestPage<a class="new" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=NewTestPage" title="create this page">?</a>')
#                          'NewTestPage<a class="new" href="/test_folder_1_/wiki/TestPage/editform?page=NewTestPage" title="create this page">?</a>')
        self.assertEquals(self.p.renderLinksIn('!TestPage'),'TestPage')
        self.assertEquals(self.p.renderLinksIn('[newpage]'),
                          '[newpage]<a class="new" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=newpage" title="create this page">?</a>')
#                          '[newpage]<a class="new" href="/test_folder_1_/wiki/TestPage/editform?page=newpage" title="create this page">?</a>')
        # a problem with escaping remote wiki links was reported
        self.p.edit(text='RemoteWikiURL: URL/')
        self.assertEquals(self.p.renderLinksIn('TestPage:REMOTEPAGE'),
                          '<a href="URL/REMOTEPAGE">TestPage:REMOTEPAGE</a>')
        self.assertEquals(self.p.renderLinksIn('!TestPage:REMOTEPAGE'),
                          'TestPage:REMOTEPAGE')
        self.assertEquals(self.p.renderLinksIn('[ ]'),
                          '[ ]<a class="new" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=%20" title="create this page">?</a>')
#                          '[ ]<a class="new" href="/test_folder_1_/wiki/TestPage/editform?page=%20" title="create this page">?</a>')
        # do display the brackets prior to page creation
        self.assertEquals(self.p.renderLinksIn('[newpage]'),
                          '[newpage]<a class="new" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=newpage" title="create this page">?</a>')
#                          '[newpage]<a class="new" href="/test_folder_1_/wiki/TestPage/editform?page=newpage" title="create this page">?</a>')
        # don't link wikinames inside <a href...>...</a>
        self.assertEquals(self.p.renderLinksIn('<a href>WikiName</a>'),
                          '<a href>WikiName</a>')
        # do link wikinames after <a name...> with no closing </a>
        self.assertEquals(self.p.renderLinksIn('<a name>WikiName'),
#                          '<a name>WikiName<a class="new" href="/test_folder_1_/wiki/TestPage/editform?page=WikiName" title="create this page">?</a>')
                          '<a name>WikiName<a class="new" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=WikiName" title="create this page">?</a>')



if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(ZWikiPageTests))
        return suite
