import os, os.path

from Products.ZWiki.testsupport import *
ZopeTestCase.installProduct('ZWiki')

from ReplaceInlineLatex import replaceInlineLatex

IMAGEDIR = os.path.join(INSTANCE_HOME,"var","LatexWiki")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):
    # XXX this is a functional test, we can't run it reliably in unit tests
    # eg it breaks depending on what user runs tests
    def Xtest_generate_image_from_latex(self):
        # image is 19 high on my system.. assume it's alright for now
        #m = re.match(r'<img alt="a" class="equation" src="images/([^"]*)" width="10" height="8">',
        m = re.match(r'<img alt="a" class="equation" src="images/([^"]+)" width="10" height="',
                     replaceInlineLatex('$a$', 17, 0.0, 1.03))
        # image tag generated ?
        self.assert_(m)
        # latexwiki image dir writable ?
        self.assert_(os.access(IMAGEDIR, os.W_OK))
        # image file exists ? XXX could have been created by a previous run
        self.assert_(os.access(os.path.join(IMAGEDIR,m.group(1)), os.R_OK)) 
