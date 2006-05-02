from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

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
    # under ZopeTestCase the page's _p_jar is present but None,
    # which makes cb_isMoveable & manage_renameObject fail.
    # hack it for the duration
    ZWikiPage.cb_isMoveable = lambda x:1 # XXX affects later tests ?
    # better, from the ZTC FAQ - but gives this:
    #  File "/usr/local/zope/software/lib/python/ZODB/Transaction.py", line 235, in commit
    #    ncommitted += self._commit_objects(objects)
    #  File "/usr/local/zope/software/lib/python/ZODB/Transaction.py", line 349, in _commit_objects
    #    jar.commit(o, self)
    #  File "/usr/local/zope/software/lib/python/ZODB/Connection.py", line 389, in commit
    #    dump(state)
    #UnpickleableError: Cannot pickle <type 'file'> objects
    #get_transaction().commit(1)
    self.wiki.TestPage.rename(pagename='NewName',REQUEST=req)
    self.assert_(hasattr(self.wiki,'NewName'))
    # the wiki outline object is also updated
    self.assert_(not self.wiki.NewName.wikiOutline().hasNode('TestPage'))
    self.assert_(self.wiki.NewName.wikiOutline().hasNode('NewName'))
    # again, this time with parents and offspring
    self.wiki.NewName.create('NewNameChild')
    self.wiki.NewNameChild.create('NewNameGrandChild')
    self.wiki.NewNameChild.rename(pagename='NewNameChildRenamed',REQUEST=req)
    self.assert_(hasattr(self.wiki,'NewNameChildRenamed'))
    self.assert_('NewNameChildRenamed' in self.wiki.NewNameGrandChild.parents)
    # the wiki outline object is also updated
    self.assert_('NewNameChildRenamed' in \
                 self.wiki.outline.parents('NewNameGrandChild'))
    self.assert_('NewName' in \
                 self.wiki.outline.parents('NewNameChildRenamed'))
    

class Tests(ZwikiTestCase):

    def test_manage_addZWikiPage(self):
        from Products.ZWiki.ZWikiPage import manage_addZWikiPage
        manage_addZWikiPage(self.folder,'ZmiTestPage')
        assert hasattr(self.folder,'ZmiTestPage')
        # the wiki outline object is also updated
        self.assert_(self.folder.ZmiTestPage.wikiOutline().hasNode('ZmiTestPage'))

    def test_edit(self):
        p = self.page
        p.edit(text='something')
        self.assertEqual(p.read(),'something')
        p.edit(text='')
        self.assertEqual(p.read(),'')

    def test__createFileOrImage(self):
        import OFS
        p = self.page
        f = p.aq_parent
        file = OFS.Image.Pdata('test file data')

        # our test page/folder initially has no uploads attr.
        self.assert_(not hasattr(p,'uploads'))

        # calling with an unnamed file should do nothing much
        self.assertEqual(p._createFileOrImage(file),(None, None, None))
        
        # ditto for a blank filename
        file.filename = ''
        self.assertEqual(p._createFileOrImage(file),(None, None, None))

        # here, a file object of unknown type should be created
        name = 'testfile'
        file.filename = name
        id, content_type,size = p._createFileOrImage(file)
        self.assertEqual(str(getattr(f,id)),'test file data')
        self.assertEqual(content_type ,'application/octet-stream')
        self.assertEqual(size,14)

        # a text file
        name = 'testfile.txt'
        file.filename = name
        id, content_type,size = p._createFileOrImage(file)
        self.assertEqual(str(f[id]),'test file data')
        self.assertEqual(content_type,'text/plain')

        # an image
        name = 'testfile.gif'
        file.filename = name
        id, content_type,size = p._createFileOrImage(file)
        # evaluating an Image gives its html tag
        self.assert_(re.match(r'<img.*testfile\.gif',str(f[id])))
        self.assertEqual(content_type,'image/gif')

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
        self.assert_(hasattr(f,'edittestfile'))
        # with the right data
        self.assertEqual(str(f['edittestfile']),'test file data')
        # and a link should have been added to the page
        #XXX do this test for each page type ?
        #self.assertEqual(p.read(),'\n\n<a href="edittestfile">edittestfile</a>\n') # stx
        self.assertEqual(p.read(),'\n\n!`edittestfile`__\n\n__ edittestfile\n')     # rst

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
        self.assert_(hasattr(f,'edittestimage.jpg'))
        self.assertEqual(f['edittestimage.jpg'].content_type,'image/jpeg')
        #self.assertEqual(p.read(),'\n\n<img src="edittestimage.jpg" />\n') #stx
        self.assertEqual(p.read(),'\n\n.. image:: edittestimage.jpg\n')     #rst

        # images should not be inlined if dontinline is set
        p.REQUEST.file.filename = 'edittestimage.png'
        p.REQUEST.dontinline = 1
        p.edit(REQUEST=p.REQUEST)
        #self.assertEqual(p.read(),
        #  '\n\n<img src="edittestimage.jpg" />\n\n\n<a href="edittestimage.png">edittestimage.png</a>\n') #stx
        self.assertEqual(p.read(),
          '\n\n.. image:: edittestimage.jpg\n\n\n!`edittestimage.png`__\n\n__ edittestimage.png\n') #rst

    def testRedirectAfterDelete(self):
        p = self.page
        p.parents = ['chickens','dogs']
        p.recycle = lambda x: None
        req = MockRequest()
        #req = makerequest(self.app)
        class MockResponse:
            def redirect(self, url): self.redirectedto = url
        req.RESPONSE = MockResponse()

        # redirect to wiki url if no existing parents
        r = p.handleDeleteMe('DeleteMe',REQUEST=req)
        self.assertEqual(r,1)
        self.assert_(hasattr(req.RESPONSE,'redirectedto'))
        self.assertEqual(req.RESPONSE.redirectedto,
                         p.wiki_url()+'/')
        
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
        #                 p.wiki_url()+'/'+'Dogs')

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
    
    # same problem as above
    #def test_recycle(self):
    #    p = mockPage(__name__='TestPage')
    #    f = p.aq_parent
    #    self.assert_(hasattr(f,'TestPage'))
    #    p.recycle()                     
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
        
    def testEditLastEditorStamping(self):
        # Username stamping
        p = self.page
        f = p.aq_parent
        p.last_editor = '-'

        # if no username available, IP address should be recorded
        p.REQUEST.set('REMOTE_ADDR', '1.2.3.4')
        p.append(text='.',REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'1.2.3.4')
        self.assertEqual(p.last_editor_ip,'1.2.3.4')

        # use the zwiki_username cookie if available
        p.REQUEST.cookies['zwiki_username'] = 'cookiename'
        p.append(text='.',REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'cookiename')
        self.assertEqual(p.last_editor_ip,'1.2.3.4')

        # if we are authenticated, use that by preference
        p.REQUEST.set('AUTHENTICATED_USER', MockUser('authusername'))
        p.append(text='.',REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'authusername')
        self.assertEqual(p.last_editor_ip,'1.2.3.4')

        # don't record editor if nothing is actually changed
        p.REQUEST.set('AUTHENTICATED_USER', MockUser('differentusername'))
        p.REQUEST.set('REMOTE_ADDR', '5.6.7.8')
        p.edit(text=p.read(),REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'authusername')
        self.assertEqual(p.last_editor_ip,'1.2.3.4')

    def test_create(self):
        p = self.page
        f = p.aq_parent
        
        # create a blank page
        p.create('TestPage1',text='')
        self.assert_(hasattr(f,'TestPage1'))
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
        self.assert_(hasattr(f,'TestPage1'))
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
        self.assertEqual(p.read(),'\ntest\n')

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
        diff = PageDiffSupport().textDiff(a=oldtext,b=text,verbose=0)
        self.assertEqual(diff,SHOULDDIFF)
        #self.assertEqual(p.formatMailout(diff), SHOULDMAILOUT)

        # a citation with no trailing newline
        p.edit(text='')
        oldtext = p.read()
        p.comment(text='> test',username=USER,time=TIME)
        text = p.read()
        text = re.sub(r'Message-ID: <[^>]+>',r'Message-ID: <>',text)
        text = re.sub(r'In-reply-to: <[^>]+>',r'In-reply-to: <>',text)
        diff = PageDiffSupport().textDiff(a=oldtext,b=text,verbose=0)
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
        diff = PageDiffSupport().textDiff(a=oldtext,b=text,verbose=0)
        self.assertEqual(diff,SHOULDDIFF)
        #self.assertEqual(p.formatMailout(diff), SHOULDMAILOUT)

    #def test_stxToHtml(self):
    #    p = self.page
    #    # handle a STX table or other error gracefully
    #    self.assertEquals(p.stxToHtml('+-+-+\n| | |\n+-+-+'),
    #                      '')

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

