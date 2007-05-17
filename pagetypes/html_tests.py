from Products.ZWiki.testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_html_page_type(self):
        self.p.edit(text='! PageOne PageTwo\n',type='html')
        self.assertEquals(self.p.render(bare=1),' PageOne PageTwo\n\n\n')
        self.p.edit(text='PageOne\n',type='html')
        self.assertEquals(
            self.p.render(bare=1),
            'PageOne<a class="new visualNoPrint" href="http://nohost/test_folder_1_/wiki/TestPage/createform?page=PageOne" title="create this page">?</a>\n\n\n')

    def test_html_page_type_with_comment(self):
        self.p.folder().allowed_page_types = ['html']
        text = """<p>A simple <b>html</b> page</p>

From betabug Thu May 17 21:31:38 +0300 2007
From: betabug
Date: Thu, 17 May 2007 21:31:38 +0300
Subject: With a comment
Message-ID: <20070517213138+0300@briareus.local:8380>

in here"""
        expected = """<p>A simple <b>html</b> page</p>\n\n\n\n<a name="comments"><br /><b><span class="commentsheader">comments:</span></b></a>\n\n\n\n<p class="commentheading"> <strong>With a comment</strong> --betabug, Thu, 17 May 2007 21:31:38 +0300 <a class="reference" href="http://nohost/test_folder_1_/wiki/TestPage?subject=With%20a%20comment&amp;in_reply_to=%3C20070517213138%2B0300%40briareus.local%3A8380%3E#bottom">reply</a>\n\n</p>in here"""
        self.p.edit(text=text,type='html')
        self.assertEquals(self.p.render(bare=1), expected)
        del self.p.folder().allowed_page_types
