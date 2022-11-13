from Products.ZWiki.tests.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_PageTypePlaintext(self):
        self.p.folder().allowed_page_types = ['plaintext']
        self.p.edit(text='! PageOne PageTwo\n',type='plaintext')
        self.assertEquals(self.p.render(bare=1),
                          '<pre>\n! PageOne PageTwo\n\n</pre>\n\n\n')
        del self.p.folder().allowed_page_types

    def test_PageTypePlaintext_with_comment(self):
        self.p.folder().allowed_page_types = ['plaintext']
        text = """with some simple text

From betabug Thu May 17 21:15:10 +0300 2007
From: betabug
Date: Thu, 17 May 2007 21:15:10 +0300
Subject: first comment
Message-ID: <20070517211510+0300@briareus.local:8380>

goes here"""
        expected = """<pre>
with some simple text
</pre>



<p>


first comment --betabug, Thu, 17 May 2007 21:15:10 +0300

<pre>
goes here
</pre>
"""
        self.p.edit(text=text,type='plaintext')
        self.assertEquals(self.p.render(bare=1), expected)
        del self.p.folder().allowed_page_types
