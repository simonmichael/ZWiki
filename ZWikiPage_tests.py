from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')
from Utils import isunicode
from Regexps import *

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_manage_addZWikiPage(self):
        self.folder.manage_addProduct['ZWiki'].manage_addZWikiPage(\
            'ZmiTestPage')
        self.assert_('ZmiTestPage' in self.folder.objectIds('ZWiki Page'))
        # the wiki outline object is also updated
        self.assert_(self.folder.ZmiTestPage.wikiOutline().hasNode('ZmiTestPage'))

    def test_incompleteCatalogReturnsNothing(self):
        # an incomplete catalog could be a plone catalog that hasn't yet
        # had the extra fields added for Zwiki, or a zwiki catalog that's
        # had some fields removed - eg IssueNo0623. We used to look up the
        # missing fields in this case, but now return no results to avoid
        # performance problems in the revisions folder.
        self.page.setupCatalog()
        self.page.catalog().manage_delColumn('parents')
        self.assertEquals(self.page.pages(),[])

    def test_canonicalIdFrom(self):
        p = self.page
        self.assertEquals(p.canonicalIdFrom('WikiName'),'WikiName')
        self.assertEquals(p.canonicalIdFrom('ZWikiWikiNames2'),'ZWikiWikiNames2')
        self.assertEquals(p.canonicalIdFrom('a page with !'),'APageWith')
        self.assertEquals(p.canonicalIdFrom('a_page'),'APage')
        self.assertEquals(p.canonicalIdFrom('Test\xc3Page'),'Test_c3Page') # A tilde
        self.assertEquals(p.canonicalIdFrom('\xc3Page'),'X_c3Page')
        self.assertEquals(p.canonicalIdFrom('_c3Page'),'C3Page')
        self.failIf(isunicode(p.canonicalIdFrom(u'Test')))

    def test_asAgeString(self):
        #p = self.page
        p = mockPage()
        self.assertEqual(p.asAgeString(p.last_edit_time),'some time')

    def test_pageIdsStartingWith(self):
        p = self.page
        p.create('TestPage2')
        self.assertEqual(p.pageIdsStartingWith('Test'),
                         ['TestPage','TestPage2'])

    def test_pageNamesStartingWith(self):
        p = self.page
        p.setupCatalog()
        p.title = 'Test Page'
        p.index_object()
        p.create('Test Page 2')
        self.assertEqual(p.pageNamesStartingWith('Test'),
                         ['Test Page','Test Page 2'])

    def test_firstPageIdStartingWith(self):
        p = self.page
        p.create('TestPage2')
        self.assertEqual(p.firstPageIdStartingWith('Test'),'TestPage')

    def test_firstPageNameStartingWith(self):
        p = self.page
        p.setupCatalog()
        p.title = 'Test Page'
        p.index_object()
        p.create('Test Page 2')
        self.assertEqual(p.firstPageNameStartingWith('Test'),'Test Page')

    def test_pageWithId(self):
        p = self.page
        self.failIf(p.pageWithId('nosuchid'))
        self.assert_(p.pageWithId('TestPage'))
        self.failIf(p.pageWithId('testpage'))
        self.assert_(p.pageWithId('testpage',ignore_case=1))

    def test_pageWithName(self):
        p = self.page
        p.title = 'Test page'
        self.assert_(p.pageWithName(p.title))

    def test_pageWithFuzzyName(self):
        p = self.page
        p.title = 'Test page'
        self.assert_(p.pageWithFuzzyName('Test page'))
        self.assert_(p.pageWithFuzzyName(' Test  page\t'))
        self.assert_(p.pageWithFuzzyName('TestPage'))
        self.assert_(p.pageWithFuzzyName('TEST Page'))
        self.assert_(p.pageWithFuzzyName('Testpage'))
        self.failIf(p.pageWithFuzzyName('test'))
        self.assert_(p.pageWithFuzzyName('test',allow_partial=1))

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

    def test_isValidWikiLinkSyntax(self):
        self.assertEquals(self.p.isValidWikiLinkSyntax('WikiName'),1)
        self.p.use_wikiname_links = 0
        self.assertEquals(self.p.isValidWikiLinkSyntax('WikiName'),0)
        self.p.use_wikiname_links = 1
        self.assertEquals(self.p.isValidWikiLinkSyntax('WikiName'),1)
        self.assertEquals(self.p.isValidWikiLinkSyntax('[freeform name]'),1)
        self.p.use_bracket_links = 0
        self.assertEquals(self.p.isValidWikiLinkSyntax('[freeform name]'),0)
        self.p.use_bracket_links = 1
        self.assertEquals(self.p.isValidWikiLinkSyntax('[freeform name]'),1)
        self.assertEquals(self.p.isValidWikiLinkSyntax('[[double brackets]]'),1)
        self.p.use_double_bracket_links = 0
        self.assertEquals(self.p.isValidWikiLinkSyntax('[[double brackets]]'),0)
        self.p.use_double_bracket_links = 1
        self.assertEquals(self.p.isValidWikiLinkSyntax('[[double brackets]]'),1)

    def test_markLinksIn(self):
        self.assertEquals(self.p.markLinksIn('test'),'test')
        self.assertEquals(self.p.markLinksIn('http://url'),
                          '<zwiki>http://url</zwiki>')
        self.assertEquals(
            self.p.markLinksIn(
            'WikiName, [freeform name], [[double brackets]], ((double parentheses))'),
            '<zwiki>WikiName</zwiki>, <zwiki>[freeform name]</zwiki>, <zwiki>[[double brackets]]</zwiki>, ((double parentheses))')
        self.p.use_wikiname_links = 0
        self.p.use_bracket_links = 0
        self.p.use_double_bracket_links = 0
        self.p.use_double_parenthesis_links = 1
        self.assertEquals(
            self.p.markLinksIn(
            'WikiName, [freeform name], [[double brackets]], ((double parentheses))'),
            'WikiName, [freeform name], [[double brackets]], <zwiki>((double parentheses))</zwiki>')

    def test_formatWikiname(self):
        self.assertEquals(self.p.formatWikiname('CamelCase'),'CamelCase')
        self.p.folder().space_wikinames = 1
        self.assertEquals(self.p.formatWikiname('CamelCase'),'Camel Case')

    def test_regexps(self):
        self.assert_(not re.search(interwikilink,'TestPage::'))

    def test_renderLink(self):
        self.assertEquals(
            self.p.renderLink('[unbalanced (]')[-53:],
            'page=unbalanced%20%28" title="create this page">?</a>')
        self.assertEquals(
            self.p.renderLink('http://some.url'),
            '<a href="http://some.url">http://some.url</a>')
        self.p.folder().space_wikinames = 1
        self.assertEquals(self.p.renderLink('CamelCase')[:10],'Camel Case')
        self.assertEquals(
            self.p.renderLink('[testpage | the label]'),
            '<a href="http://nohost/test_folder_1_/wiki/TestPage"> the label</a>')
        self.assertEquals(
            self.p.renderLink('[http://some.url|label]'),
            '<a href="http://some.url">label</a>')
        
    def test_renderLinksIn(self):
        self.assertEquals(self.p.renderLinksIn('nolink'),'nolink')
        self.assertEquals(self.p.renderLinksIn('http://a.b.c/d'),
                          '<a href="http://a.b.c/d">http://a.b.c/d</a>')
        self.assertEquals(self.p.renderLinksIn('mailto:a@b.c'),
                          '<a href="mailto:a@b.c">a@b.c</a>')
        self.assertEquals(self.p.renderLinksIn('TestPage'),
                          '<a href="http://nohost/test_folder_1_/wiki/TestPage">TestPage</a>')
#                          '<a href="/test_folder_1_/wiki/TestPage" title="" style="background-color:;">TestPage</a>')
        self.assertEquals(self.p.renderLinksIn('NewTestPage'),
                          'NewTestPage<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=NewTestPage" title="create this page">?</a>')
#                          'NewTestPage<a class="new" href="/test_folder_1_/wiki/TestPage/editform?page=NewTestPage" title="create this page">?</a>')
        self.assertEquals(self.p.renderLinksIn('!TestPage'),'TestPage')
        self.assertEquals(self.p.renderLinksIn('[newpage]'),
                          '[newpage]<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=newpage" title="create this page">?</a>')
#                          '[newpage]<a class="new visualNoPrint" href="/test_folder_1_/wiki/TestPage/editform?page=newpage" title="create this page">?</a>')
        # a problem with escaping remote wiki links was reported
        self.p.edit(text='RemoteWikiURL: URL/')
        self.assertEquals(self.p.renderLinksIn('TestPage:REMOTEPAGE'),
                          '<a href="URL/REMOTEPAGE">TestPage:REMOTEPAGE</a>')
        self.assertEquals(self.p.renderLinksIn('!TestPage:REMOTEPAGE'),
                          'TestPage:REMOTEPAGE')
        self.assertEquals(self.p.renderLinksIn('[ ]'),
                          '[ ]<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=%20" title="create this page">?</a>')
#                          '[ ]<a class="new visualNoPrint" href="/test_folder_1_/wiki/TestPage/editform?page=%20" title="create this page">?</a>')
        # do display the brackets prior to page creation
        self.assertEquals(self.p.renderLinksIn('[newpage]'),
                          '[newpage]<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=newpage" title="create this page">?</a>')
#                          '[newpage]<a class="new visualNoPrint" href="/test_folder_1_/wiki/TestPage/editform?page=newpage" title="create this page">?</a>')
        # don't link wikinames inside <a href...>...</a>
        self.assertEquals(self.p.renderLinksIn('<a href>WikiName</a>'),
                          '<a href>WikiName</a>')
        # do link wikinames after <a name...> with no closing </a>
        self.assertEquals(self.p.renderLinksIn('<a name>WikiName'),
#                          '<a name>WikiName<a class="new visualNoPrint" href="/test_folder_1_/wiki/TestPage/editform?page=WikiName" title="create this page">?</a>')
                          '<a name>WikiName<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=WikiName" title="create this page">?</a>')

    def Xtest_renderLink_speed(self):
        import time
        for i in range(999):
            self.p.create('TestPage%03d'%i)
        t = time.time()
        self.assertEquals(self.p.pageCount(),1000)
        print time.time() - t
        
    def test_displaysSubtopicsWithDtml(self):
        self.p.edit(text='')
        self.failIf(self.p.displaysSubtopicsWithDtml())
        self.p.edit(text='<dtml subtopics')
        self.failIf(self.p.displaysSubtopicsWithDtml())
        self.p.edit(text='<dtml-var subtopics')
        self.failIf(self.p.displaysSubtopicsWithDtml())
        self.p.allow_dtml = 1
        self.p.edit(text='<dtml-var subtopics')
        self.assert_(self.p.displaysSubtopicsWithDtml())
        self.p.edit(text='&dtml-subtopics')
        self.assert_(self.p.displaysSubtopicsWithDtml())

    def test_linkTitleFrom(self):
        edittime = DateTime.DateTime() - 0.2
        edittime = edittime.ISO8601()
        r = self.p.linkTitleFrom()
        self.assertEquals( r, 'last edited some time ago')
        r = self.p.linkTitleFrom(prettyprint=1) 
        self.assert_( 'some time' in r )
        self.assert_( '<a href=' in r )
        r = self.p.linkTitleFrom(last_edit_time=edittime, prettyprint=1)
        self.assert_( '4 hours' in r )
        r = self.p.linkTitleFrom(last_edit_time=edittime, \
                                 last_editor='fred', prettyprint=1)
        self.assert_( 'fred' in r )
        edittime = 'not valid'
        r = self.p.linkTitleFrom(last_edit_time=edittime)
        self.assert_( 'some time' in r )

    def test_renderMidsectionIn(self):
        from pagetypes.common import MIDSECTIONMARKER
        p = self.page
        self.assertEqual('a\nb',p.renderMidsectionIn('a'+MIDSECTIONMARKER+'b'))
        #self.assertEqual('a\n',p.renderMidsectionIn('a'+MIDSECTIONMARKER+'é'))
        self.assertEqual(u'a\n\xe9',p.renderMidsectionIn('a'+MIDSECTIONMARKER+u'\xe9'))
        
