from support import *
from Products.ZWiki.plugins.PurpleNumbers import nidexpr

class PurpleNumbersTests(unittest.TestCase):
    def setUp(self):
        self.p = MockZWikiPage().aq_parent.TestPage

    def testUsePurpleNumbersProperty(self):
        self.p.edit(text='a\n')
        self.assertEquals(self.p.read(),'a\n')
        self.p.folder().use_purple_numbers = 0
        self.p.edit(text='b\n')
        self.assertEquals(self.p.read(),'b\n')
        self.p.folder().use_purple_numbers = 1
        self.p.edit(text='c\n')
        self.assert_(re.search(nidexpr,self.p.read()))

    def test_addPurpleNumbersTo(self):
        self.assertEquals(
            self.p.addPurpleNumbersTo('a\n',self.p),
            'a {nid 1}\n'
            )
        self.assertEquals(
            self.p.addPurpleNumbersTo('b\n b\n',self.p),
            'b\n b {nid 2}\n'
            )
        self.assertEquals(
            self.p.addPurpleNumbersTo('c:: \n\n c\n',self.p),
            #'c {nid 3}:: \n\n c\n' #can't do this yet
            'c {nid 3}:: \n\n c {nid 4}\n'
            )

#    def test_addPurpleNumbersToSTX(self):
#        self.assertEquals(
#            self.p.addPurpleNumbersToSTX('a\n'),
#            'a {nid 1}\n'
#            )
#        self.assertEquals(
#            self.p.addPurpleNumbersToSTX('b\n b\n'),
#            'b\n b {nid 2}\n'
#            )
#        self.assertEquals(
#            self.p.addPurpleNumbersToSTX('c:: \n\n c\n'),
#            #'c {nid 3}:: \n\n c\n' #can't do this yet
#            'c {nid 3}:: \n\n c {nid 4}\n'
#            )
#
#    def test_addPurpleNumbersToRST(self):
#        self.p.edit(type='rst')
#        self.assertEquals(
#            self.p.addPurpleNumbersToRST('a\n'),
#            'a {nid 1}\n'
#            )
#        self.assertEquals(
#            self.p.addPurpleNumbersToRST('b\n b\n'),
#            'b\n b {nid 2}\n'
#            )
#        # can't do this yet
#        #self.assertEquals(
#        #    self.p.addPurpleNumbersToRST('ccc\n---\n'),
#        #    'ccc\n--- {nid 3}\n'
#        #    )
#
#    def test_addPurpleNumbersToWWML(self):
#        self.p.edit(type='wwml')
#        self.assertEquals(
#            self.p.addPurpleNumbersToRST('a\n'),
#            'a {nid 1}\n'
#            )
#        self.assertEquals(
#            self.p.addPurpleNumbersToRST('b\n b\n'),
#            'b\n b {nid 2}\n'
#            )

#    def test_addPurpleNumbers(self):
#        self.p.folder().use_purple_numbers = 1
#        self.p.edit(text='a\n',type='msgstxprelinkfitissuehtml')
#        self.p.addPurpleNumbers()
#        self.assertEquals(self.p.read(),'a {nid 1}\n')

    def test_renderPurpleNumbersIn(self):
        self.assertEquals(
            self.p.renderPurpleNumbersIn('<p>blah {nid 1}</p>'),
            #'<a id="nid1" name="nid1"></a><p>blah&nbsp;&nbsp;<a href="http://foo/foo/test//TestPage#nid1" class="nid" style="font-family:Helvetica,Arial,sans-serif;font-weight:bold;font-size:x-small;text-decoration:none;color:#C8A8FF">(1)</a></p>'
            # temporary, due to MZP
            '<a id="nid1" name="nid1"></a><p>blah&nbsp;&nbsp;<a href="http://foo/foo/test/TestPage//TestPage//TestPage#nid1" class="nid" style="font-family:Helvetica,Arial,sans-serif;font-weight:bold;font-size:x-small;text-decoration:none;color:#C8A8FF">(1)</a></p>'
            )

    def test_textWithoutPurpleNumbers(self):
        self.p.raw = 'blah {nid 1}'
        self.assertEquals(self.p.textWithoutPurpleNumbers(), 'blah')

    def testNidsForMessages(self):
        self.assertEquals(
            self.p.addPurpleNumbersTo(
            '''\
From unknown Wed Jul 16 17:32:00 GMT 2003
From: blah
Message-ID: <id>

body''',
            self.p),
            '''\
From unknown Wed Jul 16 17:32:00 GMT 2003
From: blah
Message-ID: <id>

body {nid 1}''')
            


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PurpleNumbersTests))
    return suite

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__ == '__main__':
    main()
