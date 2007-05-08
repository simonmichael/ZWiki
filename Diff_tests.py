from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

from Products.ZWiki.Diff import htmldiff

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

#can't test PT views yet apparently
#     def test_diff(self):
#         self.assertEqual('',self.page.diff(test=1))

    def test_textDiff(self):
        p = self.page
        self.assertEqual(p.textDiff(a='1',
                                    b='1\n2'),
                         '''
++added:
2
''')
        self.assertEqual(p.textDiff(a='1\n2',
                                    b='2'),
                         '''
--removed:
-1
''')
        self.assertEqual(p.textDiff(a='1',
                                    b='12'),
                         '''
??changed:
-1
12
''')

    def test_htmlDiff(self):
        p = self.page
        self.assertEqual(htmldiff(a='1',
                                  b='1\n2'),
                         '''
<b>added:</b><span style="color:green">
2</span>
''')
        self.assertEqual(htmldiff(a='1\n2',
                                  b='2'),
                         '''
<b>removed:</b><span style="color:red;text-decoration:line-through">
-1</span>
''')
        self.assertEqual(htmldiff(a='1',
                                  b='12'),
                         '''
<b>changed:</b><span style="color:red;text-decoration:line-through">
-1</span><span style="color:green">
12</span>
''')

    def test_revertEditsEverywhereBy(self):
        p = self.page

        # fred edits
        p.last_editor = 'fred'
        p.REQUEST.cookies['zwiki_username'] = 'fred'
        p.edit(text='test',REQUEST=p.REQUEST)
        p.append(text='1',REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'fred')

        # revert edits by joe - no change
        freds = p.read()
        p.revertEditsEverywhereBy('joe')
        self.assertEqual(p.read(), freds)
        
        # joe edits
        p.REQUEST.cookies['zwiki_username'] = 'joe'
        p.edit(text='2',REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'joe')
        self.assertNotEqual(p.read(), freds)
        
        # revert edits by joe - back to fred's version
        #can't test this yet, cf #1325
        #p.revertEditsEverywhereBy('joe')
        #self.assertEqual(p.read(), freds)
        #self.assertEqual(p.last_editor,'fred')

        # test again with a brand new page
        #new = p.create('NewPage', REQUEST=p.REQUEST)
