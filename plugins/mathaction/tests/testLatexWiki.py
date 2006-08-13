import os,sys,re
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
ZopeTestCase.installProduct('ZWiki')
ZopeTestCase.installProduct('LatexWiki')
from Products.LatexWiki.ReplaceInlineLatex import replaceInlineLatex
import unittest

sys.modules['__builtin__'].CLIENT_HOME = '/var/lib/zope/instance/default/var'
imagedir = sys.modules['__builtin__'].CLIENT_HOME + "/LatexWiki/"

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LatexWikiTests))
    return suite

def my_stxlatex(text):
    return replaceInlineLatex(text, 17, 0.0, 1.03)

class LatexWikiTests(ZopeTestCase.ZopeTestCase):
    def test_stx(self):
        g = re.match(r'<img alt="a" class="equation" src="images/([^"]*)" width="10" height="8">', \
            my_stxlatex('$a$'))
        assert os.access(imagedir + g.groups(1))
        assert(g <> None)

if __name__ == '__main__':
    framework()
