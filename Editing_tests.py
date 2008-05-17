# -*- coding: utf-8 -*-
from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')
import transaction

from Diff import textdiff

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

# defined in module scope for easier reuse in plone tests XXX ?
def test_rename(self):
    # rename needs some identification
    #self.login() # no effect ?
    req = self.request
    req.cookies['zwiki_username'] = 'testuser'

    # rename
    transaction.get().savepoint() # need a _p_jar for manage_renameObject
    self.wiki.TestPage.rename(pagename='NewName',REQUEST=req)
    self.assert_(safe_hasattr(self.wiki,'NewName'))
    # the wiki outline object is also updated
    self.assert_(not self.wiki.NewName.wikiOutline().hasNode('TestPage'))
    self.assert_(self.wiki.NewName.wikiOutline().hasNode('NewName'))

    # again, this time with parents and offspring
    self.wiki.NewName.create('NewNameChild')
    self.wiki.NewNameChild.create('NewNameGrandChild')
    transaction.get().savepoint()
    self.wiki.NewNameChild.rename(pagename='NewNameChildRenamed',REQUEST=req)
    self.assert_(safe_hasattr(self.wiki,'NewNameChildRenamed'))
    self.assert_('NewNameChildRenamed' in self.wiki.NewNameGrandChild.parents)
    # the wiki outline object is also updated
    self.assert_('NewNameChildRenamed' in \
                 self.wiki.outline.parents('NewNameGrandChild'))
    self.assert_('NewName' in \
                 self.wiki.outline.parents('NewNameChildRenamed'))

    # now with unicode
    self.wiki.NewName.rename(u'N\xe9wName')
    self.assert_('N_e9wName' in self.wiki.objectIds())
    self.assertEqual(u'N\xe9wName',self.wiki.N_e9wName.pageName())

class Tests(ZwikiTestCase):

    def testRedirectAfterDelete(self):
        p = self.page
#        p.parents = ['chickens','dogs']
# can't make this work right now
#        class MockResponse:
#            def redirect(self, url): self.redirectedto = url
#        req = MockRequest()
#        req.RESPONSE = MockResponse()

        # redirect to wiki url if no existing parents
        r = p.handleDeleteMe('DeleteMe') #,REQUEST=req)
        self.assertEqual(r,1)
#         self.assert_(hasattr(req.RESPONSE,'redirectedto'))
#         self.assertEqual(req.RESPONSE.redirectedto,
#                          p.wikiUrl()+'/')
        
        ## redirect to first existing parent
        #p.create(page='Dogs')
        ## was:
        ##r = p.handleDeleteMe('DeleteMe',REQUEST=req)
        ## started breaking when I introduced page titles.
        ## incorrect anyway, should be something like:
        #r = p.aq_parent.Dogs.handleDeleteMe('DeleteMe',REQUEST=req)
        ## but the mock page won't support this
        ## disable the lot for now
        #self.assertEqual(r,1)
        #self.assert_(hasattr(req.RESPONSE,'redirectedto'))
        #self.assertEqual(req.RESPONSE.redirectedto,
        #                 p.wikiUrl()+'/'+'Dogs')

    # can't test recycle easily, because manage_pasteObject needs an app
    #def testDeleteMe(self):
    #    #When we see a first line beginning with "DeleteMe":
    #    #- move to recycle_bin
    #    #- redirect to first parent or default page
    #
    #    p = mockPage(__name__='TestPage')
    #    f = p.aq_parent
    #    self.assert_(hasattr(f,'TestPage'))
    #    self.assert_(not hasattr(f,'recycle_bin'))
    #
    #    #deleteme's not at the beginning shouldn't do anything
    #    p.edit(text=p.read()+'\nDeleteMe')
    #    self.assertEqual(p.read(),'\nDeleteMe')
    #
    #    #deleteme at the beginning will send it to recycle_bin
    #    p.edit(text='DeleteMe, with comments\n')
    #    self.assert_(not hasattr(f,'TestPage'))
    #    self.assert_(hasattr(f,'recycle_bin'))
    #    self.assertEqual(f.recycle_bin.TestPage.read(),'\nDeleteMe')
    
    #def test_delete(self):
        #p = mockPage()
        #f = p.folder()
        #self.assert_(hasattr(f,'TestPage'))
        #p.delete()
        #self.assert_(not hasattr(f,'TestPage'))
        #self.assert_(hasattr(f,'recycle_bin'))
        #self.assert_(hasattr(f.recycle_bin,'TestPage'))

    # failed to make this test work
    #def test_delete_leaves_no_orphans(self):
    #    p = mockPage(__name__='Page')
    #    f = p.folder()
    #    # create() would give real zwiki pages, build these by hand
    #    child = mockPage(__name__='Child')
    #    f._setObject('Child',child,set_owner=0)
    #    child.parents = ['Page']
    #    grandchild = mockPage(__name__='GrandChild')
    #    f._setObject('GrandChild',grandchild,set_owner=0)
    #    grandchild.parents = ['Child']
    #    child.recycle = lambda x: None
    #    child.REQUEST.cookies['zwiki_username'] = 'someusername'
    #    child.delete(REQUEST=child.REQUEST)
    #    self.assertEquals(grandchild.parents,['Page'])

    def test_edit(self):
        p = self.page
        p.edit(text='something')
        self.assertEqual(p.read(),'something')
        p.edit(text='')
        self.assertEqual(p.read(),'')

    def test__addFileFromRequest(self):
        import OFS
        p = self.page
        f = p.aq_parent
        file = OFS.Image.Pdata('test file data')
        p.REQUEST.file = file

        # our test page/folder initially has no uploads attr.
        self.assert_(not safe_hasattr(p,'uploads'))

        # calling with an unnamed file should do nothing much
        self.assertEqual(p._addFileFromRequest(p.REQUEST),None)
        
        # ditto for a blank filename
        file.filename = ''
        self.assertEqual(p._addFileFromRequest(p.REQUEST),None)

        # here, a file object of unknown type should be created
        name = 'testfile'
        file.filename = name
        id = p._addFileFromRequest(p.REQUEST)
        ob = f[id]
        self.assertEqual(str(ob),'test file data')
        self.assertEqual(ob.content_type ,'application/octet-stream')
        self.assertEqual(ob.getSize(),14)

        # a text file
        name = 'testfile.txt'
        file.filename = name
        id = p._addFileFromRequest(p.REQUEST)
        ob = f[id]
        self.assertEqual(str(ob),'test file data')
        self.assertEqual(ob.content_type,'text/plain')

        # an image
        name = 'testfile.gif'
        file.filename = name
        id = p._addFileFromRequest(p.REQUEST)
        self.assert_(re.match(r'<img.*testfile\.gif',str(f[id])))
#XXX
#         self.assertEqual(content_type,'image/gif')

    def testEditWithFileUpload(self):
        import OFS
        p = self.page
        f = p.aq_parent

        # add a file to a page
        file = OFS.Image.Pdata('test file data')
        file.filename = 'edittestfile'
        p.REQUEST.file = file
        p.edit(REQUEST=p.REQUEST)

        # the new file should exist
        self.assert_(safe_hasattr(f,'edittestfile'))
        # with the right data
        self.assertEqual(str(f['edittestfile']),'test file data')
        # and a link should have been added to the page
        self.assertEqual(p.read(),'\n\n!`edittestfile`__\n\n__ http://nohost/test_folder_1_/wiki/edittestfile\n')     # rst

        # a file with blank filename should be ignored
        p.REQUEST.file.filename = ''
        old = p.read()
        p.edit(REQUEST=p.REQUEST)
        self.assert_(p.read() == old)

        ## ditto, with an image
        p.edit(text='')
        file = OFS.Image.Pdata('test file data')
        file.filename = 'edittestimage.jpg'
        p.REQUEST.file = file
        p.edit(REQUEST=p.REQUEST)
        self.assert_(safe_hasattr(f,'edittestimage.jpg'))
        self.assertEqual(f['edittestimage.jpg'].content_type,'image/jpeg')
        #self.assertEqual(p.read(),'\n\n<img src="edittestimage.jpg" />\n') #stx
        self.assertEqual(p.read(),'\n\n.. image:: http://nohost/test_folder_1_/wiki/edittestimage.jpg\n')     #rst

        # images should not be inlined if dontinline is set
        p.REQUEST.file.filename = 'edittestimage.png'
        p.REQUEST.dontinline = 1
        p.edit(REQUEST=p.REQUEST)
        #self.assertEqual(p.read(),
        #  '\n\n<img src="edittestimage.jpg" />\n\n\n<a href="edittestimage.png">edittestimage.png</a>\n') #stx
        self.assertEqual(p.read(),
          '\n\n.. image:: http://nohost/test_folder_1_/wiki/edittestimage.jpg\n\n\n!`edittestimage.png`__\n\n__ http://nohost/test_folder_1_/wiki/edittestimage.png\n') #rst

    def test_edit_saves_last_editor(self):
        p = self.page
        f = p.aq_parent
        p.last_editor = '-'

        # if no username available, IP address should be recorded
        p.REQUEST.set('REMOTE_ADDR', '1.2.3.4')
        p.append(text='.',REQUEST=p.REQUEST)
        self.assertEqual(p.lastEditor(),'1.2.3.4')
        self.assertEqual(p.lastEditorIp(),'1.2.3.4')

        # use the zwiki_username cookie if available
        p.REQUEST.cookies['zwiki_username'] = 'cookiename'
        p.append(text='.',REQUEST=p.REQUEST)
        self.assertEqual(p.lastEditor(),'cookiename')
        self.assertEqual(p.lastEditorIp(),'1.2.3.4')

        # if we are authenticated, use that by preference
        p.REQUEST.set('AUTHENTICATED_USER', MockUser('authusername'))
        p.append(text='.',REQUEST=p.REQUEST)
        self.assertEqual(p.lastEditor(),'authusername')
        self.assertEqual(p.lastEditorIp(),'1.2.3.4')

        # don't record editor if nothing is actually changed
        p.REQUEST.set('AUTHENTICATED_USER', MockUser('differentusername'))
        p.REQUEST.set('REMOTE_ADDR', '5.6.7.8')
        p.edit(text=p.read(),REQUEST=p.REQUEST)
        self.assertEqual(p.lastEditor(),'authusername')
        self.assertEqual(p.lastEditorIp(),'1.2.3.4')

    def test_lastEditor(self):
        p = self.page
        # last_editor is now unicode, but handle old utf8-encoded ones
        p.last_editor = u'\xe4\xf6'        # unicode
        self.assertEqual(u'\xe4\xf6',p.lastEditor())
        p.last_editor = '\xc3\xa4\xc3\xb6' # utf8
        self.assertEqual(u'\xe4\xf6',p.lastEditor())

    def test_setLastEditor(self):
        p = self.page
        p.REQUEST.set('REMOTE_ADDR', '1.2.3.4')
        p.REQUEST.set('AUTHENTICATED_USER', MockUser('user'))
        p.setLastEditor(REQUEST=p.REQUEST)
        self.assertEqual(p.lastEditor(),'user')
        self.assertEqual(p.lastEditorIp(),'1.2.3.4')

    def test_setText(self):
        p = self.page
        p.edit(text='<html blah>\n<body blah>\ntest\n</body>\n</html>')
        # we don't strip stuff outside body tags any more
        #self.assertEqual(p.read(),'\ntest\n')
        self.assertEqual(p.read(),u'<html blah>\n<body blah>\ntest\n</body>\n</html>')

    def test_setCreator(self):
        p = self.page
        r = MockRequest()
        u = MockUser('test user')
        r.set('AUTHENTICATED_USER',u)
        r.set('REMOTE_ADDR','4.3.2.1')
        p.setCreator()
        self.assert_(p.creation_time)
        self.assertEqual(p.creator_ip,'')
        self.assertEqual(p.creator,'')
        p.setCreator(r)
        self.assertEqual(p.creator_ip,'4.3.2.1')
        self.assertEqual(p.creator,'test user')
        
    def test_text(self):
        p = self.page
        # ensure we don't lose first lines to DTML's decapitate()
        p.setText(r'first: line\n\nsecond line\n')
        self.assertEqual(p.text(),'first: line\\n\\nsecond line\\n')
        # ensure none of these reveal the antidecapkludge
        p.edit(type='html')
        p.setText('test text')
        self.assertEqual(p.text(),'test text')
        self.assertEqual(p.read(),'test text')
        self.assertEqual(p.__str__(),'test text')

    def test_create(self):
        p = self.page
        f = p.aq_parent
        
        # create a blank page
        p.create('TestPage1',text='')
        self.assert_(safe_hasattr(f,'TestPage1'))
        self.assertEqual(f.TestPage1.text(),'')
        # the wiki outline object is also updated
        self.assert_(p.wikiOutline().hasNode('TestPage1'))
        # the parent is the creating page
        self.assertEqual(f.TestPage1.parents,['TestPage'])
        # or can be specified..
        p.create('TestPageA',parents=['a','b'])
        self.assertEqual(f.TestPageA.parents,['a','b'])
        p.create('TestPageB',parents=[])
        self.assertEqual(f.TestPageB.parents,[])
        
        # create a wwml page with some text
        p.create('TestPage2',text='test page data',type='wwml')
        self.assert_(safe_hasattr(f,'TestPage1'))
        self.assertEqual(f.TestPage2.read(),'test page data')
        self.assertEqual(f.TestPage2.pageTypeId(),'wwml')

# having trouble making MZP support this
# handleFileUpload -> checkPermission(,MZP.folder()) loops
# because page.aq_parent.aq_parent == page
# even if you set it to None, somewhere it comes back
#    def testCreateWithFileUpload(self):
#        p = mockPage()
#        f = p.folder()
#        f.aq_parent = None
#        
#        # upload a file while creating a page
#        # this capability broke - fix if ever needed
#        # and most of this is tested above I think
#        file = OFS.Image.Pdata('test file data')
#        file.filename = 'test_file'
#        p.REQUEST.file = file
#        p.create('TestPage3',text='test page data',REQUEST=p.REQUEST)
#        # the new file should exist
#        self.assert_(hasattr(f,'test_file'))
#        # with the right data
#        self.assertEqual(str(f['test_file']),'test file data')
#        # and a link should have been added to the new wiki page
#        self.assertEqual(f.TestPage3.read(),
#          'test page data\n\n<a href="test_file">test_file</a>\n')
#
#        # ditto with an image
#        file.filename = 'test_image.gif'
#        p.REQUEST.file = file
#        f.TestPage.create('TestPage4',text='test page data',REQUEST=p.REQUEST)
#        self.assert_(hasattr(f,'test_image.gif'))
#        self.assertEqual(f['test_image.gif'].content_type,'image/gif')
#        self.assertEqual(f.TestPage4.read(),
#                         'test page data\n\n<img src="test_image.gif">\n')
#
#        # images should not be inlined if dontinline is set
#        file.filename = 'test_image.JPG'
#        p.REQUEST.dontinline = 1
#        f.TestPage.create('TestPage5',text='',REQUEST=p.REQUEST)
#        self.assertEqual(f.TestPage5.read(),
#                         '\n\n<a href="test_image.JPG">test_image.JPG</a>\n')

    def test_setText(self):
        p = self.page
        p.edit(text='<html blah>\n<body blah>\ntest\n</body>\n</html>')
        # since 0.60, we no longer strip things outside <body> tags
        self.assertEqual(
            p.read(),
            '<html blah>\n<body blah>\ntest\n</body>\n</html>')

    def test_setLastEditor(self):
        p = self.page
        p.REQUEST.set('REMOTE_ADDR', '1.2.3.4')
        p.REQUEST.set('AUTHENTICATED_USER', MockUser('user'))
        p.setLastEditor(REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'user')
        self.assertEqual(p.last_editor_ip,'1.2.3.4')

    def test_setCreator(self):
        p = self.page
        r = MockRequest()
        u = MockUser('test user')
        r.set('AUTHENTICATED_USER',u)
        r.set('REMOTE_ADDR','4.3.2.1')
        p.setCreator()
        self.assert_(p.creation_time)
        self.assertEqual(p.creator_ip,'')
        self.assertEqual(p.creator,'')
        p.setCreator(r)
        self.assertEqual(p.creator_ip,'4.3.2.1')
        self.assertEqual(p.creator,'test user')
        
    def test_text(self):
        p = self.page
        # ensure we don't lose first lines to DTML's decapitate()
        p.setText(r'first: line\n\nsecond line\n')
        self.assertEqual(p.text(),'first: line\\n\\nsecond line\\n')
        # ensure none of these reveal the antidecapkludge
        p.edit(type='html')
        p.setText('test text')
        self.assertEqual(p.text(),'test text')
        self.assertEqual(p.read(),'test text')
        self.assertEqual(p.__str__(),'test text')

    test_rename = test_rename

    # MZP doesn't support manage_renameObject
    #def testRenameLeavesNoOrphans(self):
    #    p = mockPage('parent page')
    #    c = p.create('child page')
    #    p.rename('new parent name')
    #    self.assertEquals(['new parent name'],c.parents)

    def comment(self):
        p = self.page
        p.edit(text='test')

        # check that page source has changed after a comment
        p.comment(text='comment',username='me',time='1999/12/31 GMT')
        self.assertEqual(
            p.read(),
            '''\
test

From me Fri Dec 31 00:00:00 GMT 1999
From: me
Date: 1999/12/31 GMT
Subject: 
Message-ID: <19991231000000+0000@foo>

comment''')
        # check that the html cache has also been updated,
        # and a discussion separator added
        # XXX this was one of those "copy & paste" tests.. note the
        # underlining of _1_ in the date heading, this is not what we
        # want.
        self.assertEqual(
            p.preRendered(),
            '''\
<p>test
ZWIKIMIDSECTION</p>
<p><a name="comments"><br /><b><span class="commentsheader">comments:</span></b></a></p>
<p><a name="msg19991231000000+0000@foo"></a>
<b>...</b> --me,  <a href="http://nohost/test_folder<u>1</u>/wiki/TestPage#msg19991231000000+0000@foo">1999/12/31 GMT</a> <a href="http://nohost/test_folder<u>1</u>/wiki/TestPage?subject=&in_reply_to=%3C19991231000000%2B0000%40foo%3E#bottom">reply</a><br />
comment</p>
''')

        # check there's at most one separator
        p.comment(text='comment',username='me',time='1999/12/31 GMT')
        self.assertEqual(
            p.preRendered(),
            '''\
<p>test
ZWIKIMIDSECTION</p>
<p><a name="comments"><br /><b><span class="commentsheader">comments:</span></b></a></p>
<p><a name="msg19991231000000+0000@foo"></a>
<b>...</b> --me,  <a href="http://nohost/test_folder<u>1</u>/wiki/TestPage#msg19991231000000+0000@foo">1999/12/31 GMT</a> <a href="http://nohost/test_folder<u>1</u>/wiki/TestPage?subject=&in_reply_to=%3C19991231000000%2B0000%40foo%3E#bottom">reply</a><br />
comment</p>
<p><a name="msg19991231000000+0000@foo"></a>
<b>...</b> --me,  <a href="http://nohost/test_folder<u>1</u>/wiki/TestPage#msg19991231000000+0000@foo">1999/12/31 GMT</a> <a href="http://nohost/test_folder<u>1</u>/wiki/TestPage?subject=&in_reply_to=%3C19991231000000%2B0000%40foo%3E#bottom">reply</a><br />
comment</p>
''')
        
        # check we ignore comments with no subject or body
        old = p.read()
        p.comment(text='',subject_heading='')
        self.assertEqual(p.read(),old)

    def testEndToEndCommentFormatting(self):
        USER = "me"
        TIME = "Fri, 31 Dec 1999 00:00:00 +0000"
        COMMENT = """\
short lines

aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa
aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa

long lines

bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb
bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb

citations

> cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc
> cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc

long citations

> dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dd
> dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dd
"""
        SHOULDWRITE = """\


From me Fri Dec 31 00:00:00 +0000 1999
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: base64
From: me
Date: Fri, 31 Dec 1999 00:00:00 +0000
Subject: 
Message-ID: <>

short lines

aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa
aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa

long lines

bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb
bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb

citations

> cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc
> cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc

long citations

> dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dd
> dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dd
"""
        SHOULDDIFF = """\


From me Fri Dec 31 00:00:00 +0000 1999
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: base64
From: me
Date: Fri, 31 Dec 1999 00:00:00 +0000
Subject: 
Message-ID: <>

short lines

aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa
aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa

long lines

bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb
bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb

citations

> cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc
> cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc

long citations

> dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dd
> dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dd

"""
        # XXX this is getting confused
        SHOULDMAILOUT = """\
From me Fri Dec 31 00:00:00 +0000 1999 From: me Date: Fri, 31 Dec 1999
00:00:00 +0000 Subject: Message-ID: <>

short lines

aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa
aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa

long lines

bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb
bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb bbbb
bbbb bbbb bbbb bbbb

citations

> cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc cccc
> cccc cccc cccc cccc cccc cccc cccc cccc cccc

long citations

> dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd
> dddd dddd dd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd
> dddd dddd dddd dddd dd"""
        COMMENT2 = "bah\n"
        SHOULDWRITE2 = "\n\nbah\n"
        SHOULDDIFF2 = "\n\nbah\n\n"
        SHOULDMAILOUT2 = "bah\n"

        from Products.ZWiki.Diff import PageDiffSupport
        p = self.page

        # test formatting at each stage
        oldtext = p.read()
        p.comment(text=COMMENT,username=USER,time=TIME)
        text = p.read()
        text = re.sub(r'Message-ID: <[^>]+>',r'Message-ID: <>',text)
        text = re.sub(r'In-reply-to: <[^>]+>',r'In-reply-to: <>',text)
        self.assertEqual(text,SHOULDWRITE)
        diff = textdiff(a=oldtext,b=text,verbose=0)
        self.assertEqual(diff,SHOULDDIFF)
        #self.assertEqual(p.formatMailout(diff), SHOULDMAILOUT)

        # a citation with no trailing newline
        p.edit(text='')
        oldtext = p.read()
        p.comment(text='> test',username=USER,time=TIME)
        text = p.read()
        text = re.sub(r'Message-ID: <[^>]+>',r'Message-ID: <>',text)
        text = re.sub(r'In-reply-to: <[^>]+>',r'In-reply-to: <>',text)
        diff = textdiff(a=oldtext,b=text,verbose=0)
        #self.assertEqual(p.formatMailout(diff),
#                         """\
#From me Fri Dec 31 00:00:00 +0000 1999 From: me Date: Fri, 31 Dec 1999
#00:00:00 +0000 Subject: Message-ID: <>
#
#> test
#""")

        # with 'edits' mailout policy (so edit sends the mailout, not comment)
        p.folder().mailout_policy = 'edits'
        p.edit(text='')
        oldtext = p.read()
        p.comment(text=COMMENT,username=USER,time=TIME)
        text = p.read()
        text = re.sub(r'Message-ID: <[^>]+>',r'Message-ID: <>',text)
        text = re.sub(r'In-reply-to: <[^>]+>',r'In-reply-to: <>',text)
        self.assertEqual(text,SHOULDWRITE)
        diff = textdiff(a=oldtext,b=text,verbose=0)
        self.assertEqual(diff,SHOULDDIFF)
        #self.assertEqual(p.formatMailout(diff), SHOULDMAILOUT)

    def XXXtestNoDoubleHtmlTag(self):
        p = self.page
        p.edit(type='stx')
        text = p.render()     # slow! why ?
        self.assertEquals(len(re.findall(r'(?i)<html',text)),1)
        self.assertEquals(len(re.findall(r'(?i)<body',text)),1)

    def test_split_and_merge(self):
        p = self.page
        TEXT = """\
zero

xxx

FIRST
=====
one

aaa

SECOND
======
two

bbb
"""
        # test split
        p.edit(text=TEXT)
        p.split()
        self.assertEquals(p.text(),'zero\n\nxxx')
        self.assert_(p.pageWithName('FIRST'))
        self.assertEquals(p.pageWithName('FIRST').text(),'one\n\naaa')
        self.assert_(p.pageWithName('SECOND'))
        self.assertEquals(p.pageWithName('SECOND').text(),'two\n\nbbb')
        # test merge
        #p.merge()
        #self.assertEquals(p.text(),TEXT)

    def test_expunge(self):
        p = self.page
        p.append(text='x')
        p.append(text='x')
        p.append(text='x')
        self.assertEqual(4,p.revisionCount())
        p.render(bare=1)
        p.expunge(1)
        p = p.pageWithId(p.getId()) # the object has been replaced
        self.assertEqual(1,p.revisionCount())
        self.assertEqual(1,p.revisionNumber())
        p.render(bare=1)

    def test_expungeEditsBy(self):
        p = self.page

        # fred edits
        p.last_editor = 'fred'
        p.REQUEST.cookies['zwiki_username'] = 'fred'
        p.edit(text='test',REQUEST=p.REQUEST)
        p.append(text='1',REQUEST=p.REQUEST)
        self.assertEqual(p.lastEditor(),'fred')

        # expunge edits by joe - no change
        freds = p.read()
        p.expungeEditsBy('joe')
        self.assertEqual(p.read(), freds)
        
        # joe edits
        p.REQUEST.cookies['zwiki_username'] = 'joe'
        p.edit(text='2',REQUEST=p.REQUEST)
        self.assertEqual(p.lastEditor(),'joe')
        self.assertNotEqual(p.read(), freds)
        
        # expunge edits by joe - back to fred's version
        #can't test this yet, cf #1325
        #p.expungeEditsBy('joe')
        #self.assertEqual(p.read(), freds)
        #self.assertEqual(p.lastEditor(),'fred')

        # test again with a brand new page
        #new = p.create('NewPage', REQUEST=p.REQUEST)

    def test_comment(self):
        p = self.page
        p.comment(text='a')
        p.render(bare=1)
        # non-ascii
        # try to exercise a bug where we wrote unicode in the transaction note
        # didn't work
        p.comment(text=u'\xc9', subject_heading=u'\xc9')
        import transaction
        transaction.get().commit()
        p.render(bare=1)
        
    def test_expungeLastEditor(self):
        p, r = self.page, self.request
        def be(u):r.cookies['zwiki_username'] = u
        be('joe')
        p.append('x',REQUEST=r)
        be('jim')
        p.append('x',REQUEST=r)
        be('joe')
        p.append('x',REQUEST=r)
        p.append('x',REQUEST=r)

        self.assertEqual(5,p.revisionCount())
        self.assertEqual('joe',p.last_editor)

        def expungeLastEditorAndRefresh():
            p.expungeLastEditor()
            return p.pageWithId(p.getId())

        p = expungeLastEditorAndRefresh()
        self.assertEqual(3,p.revisionCount())
        self.assertEqual('jim',p.last_editor)

        p = expungeLastEditorAndRefresh()
        self.assertEqual(2,p.revisionCount())
        self.assertEqual('joe',p.last_editor)

        p = expungeLastEditorAndRefresh()
        self.assertEqual(1,p.revisionCount())
        self.assertEqual('',p.last_editor)
        
    def test_expungeLastEditorEverywhere(self):
        a, r = self.page, self.request
        def be(u):r.cookies['zwiki_username'] = u
        b = a.pageWithName(a.create('B'))
        b.append('x',REQUEST=r)
        be('joe')
        b.append('x',REQUEST=r)
        c = a.pageWithName(a.create('C'))
        be('jim')
        c.append('x',REQUEST=r)

        self.assertEqual([1,3,2], [p.revisionCount() for p in [a,b,c]])
            
        def expungeLastEditorEverywhereAndRefresh(p):
            p.expungeLastEditorEverywhere()
            return [p.pageWithId(q.getId()) for q in [a,b,c]]

        a,b,c = expungeLastEditorEverywhereAndRefresh(c) # removes jim
        self.assertEqual([1,3,1], [p.revisionCount() for p in [a,b,c]])

        a,b,c = expungeLastEditorEverywhereAndRefresh(b) # removes joe, but not page creation
        self.assertEqual([1,2,1], [p.revisionCount() for p in [a,b,c]])

