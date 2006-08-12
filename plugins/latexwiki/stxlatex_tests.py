from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZWiki')
#ZopeTestCase.installProduct('ZCatalog')

sys.modules['__builtin__'].CLIENT_HOME = '/var/lib/zope/instance/default/var'
imagedir = sys.modules['__builtin__'].CLIENT_HOME + "/LatexWiki/"

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

def my_stxlatex(text):
    return replaceInlineLatex(text, 17, 0.0, 1.03)

class Tests(ZwikiTestCase):
    #def afterSetUp(self):
    #    ZwikiTestCase.afterSetUp(self)
    #    self.p.setupTracker()

    def test_stxlatex(self):
        g = re.match(r'<img alt="a" class="equation" src="images/([^"]*)" width="10" height="8">', \
            my_stxlatex('$a$'))
        self.assert_(os.access(imagedir + g.groups(1)))
        self.assertNotEquals(g, None)
