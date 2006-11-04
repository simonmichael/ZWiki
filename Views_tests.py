from testsupport import *
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    suite.addTest(unittest.makeSuite(BindingsTests))
    return suite

class Tests(ZwikiTestCase):

    def test_templatesHaveMetaType(self):
        TEMPLATES = ZWiki.Views.TEMPLATES
        # make sure all default templates have meta_type
        self.failIf(filter(lambda x:not hasattr(x,'meta_type'),TEMPLATES.values()))

class BindingsTests(ZwikiTestCase):
    """
    Tests of template bindings and acquisition context, for eg #1285 and #1220.

    I want to test that "container" is the current page's folder in all cases.
    """
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        #self.folder.template = PageTemplate('test')

    def checkContainerIsFolder(self, template):
        container = re.match(r'container=(.*)', template(self.page,self.request)).group(1)
        self.assertEquals(container, repr(self.page.folder()))        

    """
    standard wiki:
     uncustomised template from fs
    """
    def test_bindingsCase1(self):
        template = self.page.getSkinTemplate('testtemplate')
        self.checkContainerIsFolder(template)

    """
     customised template from wiki folder
    """
    def Xtest_bindingsCase2(self):
        template = self.page.getSkinTemplate('testtemplate')
        self.assertEquals(
            repr(template),
            '<PageTemplateFile at /test_folder_1_/wiki/testtemplate used for /test_folder_1_/wiki/TestPage>'
            )
        installTemplateInZodb(self.folder, template)
        template = self.page.getSkinTemplate('testtemplate')
        self.assertEquals(
            repr(template),
            '<ZopePageTemplate at /test_folder_1_/wiki/testtemplate used for /test_folder_1_/wiki/TestPage>'
            ) # actually '<ZopePageTemplate at /test_folder_1_/testtemplate used for /test_folder_1_/wiki/TestPage>'
        self.checkContainerIsFolder(template)

    """
     customised template acquired from parent folder
    """
    def Xtest_bindingsCase3(self):
        template = self.page.getSkinTemplate('testtemplate')
        self.assertEquals(
            repr(template),
            '<PageTemplateFile at /test_folder_1_/wiki/testtemplate used for /test_folder_1_/wiki/TestPage>'
            )
        installTemplateInZodb(self.folder.aq_parent, template)
        template = self.page.getSkinTemplate('testtemplate')
        self.assertEquals(
            repr(template),
            '<ZopePageTemplate at /test_folder_1_/testtemplate used for /test_folder_1_/wiki/TestPage>'
            ) # actually '<ZopePageTemplate at /testtemplate used for /test_folder_1_/wiki/TestPage>'
        
        self.checkContainerIsFolder(template)

    """
    plone wiki, in a subfolder, not the root
     uncustomised fs template from portal_skins/zwiki
    """
    def test_bindingsCase4(self):
        pass

    """
     customised zodb template from portal_skins/custom
    """
    def test_bindingsCase5(self):
        pass

    """
     customised template from wiki folder
    """
    def test_bindingsCase6(self):
        pass

    """
     customised template acquired from parent folder
    """
    def test_bindingsCase7(self):
        pass


from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate

def installTemplateInZodb(folder, template):
    obj = ZopePageTemplate(template.getId(), template._text, template.content_type)
    obj.expand = 0
    obj.write(template.read())
    id = obj.getId()
    folder._setObject(id, obj)
