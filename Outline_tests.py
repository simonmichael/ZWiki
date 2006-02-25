from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')
from Products.ZWiki.Outline import Outline
#or to test it alone, just set up your pythonpath and do
#from Outline import Outline

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(unittest.TestCase):
    def setUp(self):
        self.outline = Outline(
            {
            'RootPage':[],
            'ChildPage':['RootPage'],
            'GrandChildPage':['ChildPage'],
            'SingletonPage':[],
            'TestPage':[],
            })

    def test_init(self):
        o = Outline({1:[],2:[],3:[]})
        self.assertEquals(o.nodeCount(),3)

    def test_parentmap(self):
        o = self.outline
        parentmap = o.parentmap()
        self.assertEquals(len(parentmap.keys()),5)
        self.assertEquals(parentmap['RootPage'],[])
        self.assertEquals(parentmap['ChildPage'],['RootPage'])
        self.assertEquals(parentmap['GrandChildPage'],['ChildPage'])
        self.assertEquals(parentmap['SingletonPage'],[])
        self.assertEquals(parentmap['TestPage'],[])

    def test_childmap(self):
        o = self.outline
        childmap = o.childmap()
        self.assertEquals(len(childmap.keys()),5)
        self.assertEquals(childmap['RootPage'],['ChildPage'])
        self.assertEquals(childmap['ChildPage'],['GrandChildPage'])
        self.assertEquals(childmap['GrandChildPage'],[])
        self.assertEquals(childmap['SingletonPage'],[])
        self.assertEquals(childmap['TestPage'],[])

    def test_roots(self):
        o = self.outline
        self.assertEquals(o.roots(),['RootPage','SingletonPage','TestPage'])

    def test_nodes(self):
        o = self.outline
        self.assertEquals(o.nodes(),
                          ['ChildPage','GrandChildPage','RootPage',
                           'SingletonPage','TestPage'])

    def test_flat(self):
        o = self.outline
        self.assertEquals(o.flat(),
                          ['RootPage','ChildPage','GrandChildPage',
                           'SingletonPage','TestPage'])

    def test_nesting(self):
        o = self.outline
        self.assertEquals(o.nesting(),
                          [
                           ['RootPage',
                            ['ChildPage',
                             'GrandChildPage']],
                           'SingletonPage',
                           'TestPage',
                           ])
        
    def test_next(self):
        o = self.outline
        self.assertEquals(o.next('RootPage'),'ChildPage')
        self.assertEquals(o.next('GrandChildPage'),'SingletonPage')
        self.assertEquals(o.next('TestPage'),None)

    def test_previous(self):
        o = self.outline
        self.assertEquals(o.previous('RootPage'),None)
        self.assertEquals(o.previous('ChildPage'),'RootPage')
        self.assertEquals(o.previous('SingletonPage'),'GrandChildPage')

    def test_ancestors(self):
        o = self.outline
        self.assertEquals(o.ancestors('RootPage'),[['RootPage']])
        self.assertEquals(o.ancestors('ChildPage'),[['RootPage','ChildPage']])
        self.assertEquals(o.ancestors('GrandChildPage'),
                          [['RootPage',['ChildPage','GrandChildPage']]])

    def test_ancestorsAndSiblings(self):
        o = self.outline
        self.assertEquals(o.ancestorsAndSiblings('RootPage'),
                          [['RootPage']])
        self.assertEquals(o.ancestorsAndSiblings('ChildPage'),
                          [['RootPage', 'ChildPage']])
        self.assertEquals(o.ancestorsAndSiblings('GrandChildPage'),
                          [['RootPage',['ChildPage','GrandChildPage']]])

    def test_ancestorsAndChildren(self):
        o = self.outline
        self.assertEquals(o.ancestorsAndChildren('RootPage'),
                          [['RootPage','ChildPage']])
        self.assertEquals(o.ancestorsAndChildren('ChildPage'),
                          [['RootPage', ['ChildPage','GrandChildPage']]])
        self.assertEquals(o.ancestorsAndChildren('GrandChildPage'),
                          [['RootPage',['ChildPage','GrandChildPage']]])

    def test_offspring(self):
        o = self.outline
        self.assertEquals(o.offspring(['RootPage']),
                          [['RootPage',['ChildPage','GrandChildPage']]])
        self.assertEquals(o.offspring(['ChildPage']),
                          [['ChildPage','GrandChildPage']])
        self.assertEquals(o.offspring(['GrandChildPage']),
                          ['GrandChildPage'])
        self.assertEquals(o.offspring(['RootPage'],depth=1),
                          [['RootPage','ChildPage']])
        self.assertEquals(o.offspring(['RootPage'],depth=2),
                          [['RootPage',['ChildPage','GrandChildPage']]])
    
    def test_parents(self):
        o = self.outline
        self.assertEquals(o.parents('RootPage'),[])
        self.assertEquals(o.parents('ChildPage'),['RootPage'])

    def test_siblings(self):
        o = self.outline
        self.assertEquals(o.siblings('RootPage'),['SingletonPage','TestPage'])
        self.assertEquals(o.siblings('ChildPage'),[])

    def test_children(self):
        o = self.outline
        self.assertEquals(o.children('RootPage'),['ChildPage'])
        self.assertEquals(o.children('GrandChildPage'),[])

    def test_add(self):
        o = self.outline
        self.assert_(not o.hasNode('NewPageOne'))
        o.add('NewPageOne')
        self.assert_(o.hasNode('NewPageOne'))

    def test_delete(self):
        o = self.outline
        count = o.nodeCount()
        o.delete('TestPage')
        self.assertEquals(o.nodeCount(),count-1)
        # any children should be reparented
        self.assertEquals(o.nesting(),
                          [
                           ['RootPage',
                            ['ChildPage',
                             'GrandChildPage']],
                           'SingletonPage',
                           ])
        o.delete('ChildPage')
        self.assertEquals(o.nesting(),
                          [
                           ['RootPage',
                            'GrandChildPage'],
                           'SingletonPage',
                           ])
        parentmap = o.parentmap()
        self.assertEquals(len(parentmap.keys()),3)
        self.assertEquals(parentmap['RootPage'],[])
        self.assertEquals(parentmap['GrandChildPage'],['RootPage'])
        self.assertEquals(parentmap['SingletonPage'],[])
        childmap = o.childmap()
        self.assertEquals(len(childmap.keys()),3)
        self.assertEquals(childmap['RootPage'],['GrandChildPage'])
        self.assertEquals(childmap['GrandChildPage'],[])
        self.assertEquals(childmap['SingletonPage'],[])
        o.delete('RootPage')
        self.assertEquals(o.nesting(),
                          [
                           'GrandChildPage',
                           'SingletonPage',
                           ])
        parentmap = o.parentmap()
        self.assertEquals(len(parentmap.keys()),2)
        self.assertEquals(parentmap['GrandChildPage'],[])
        self.assertEquals(parentmap['SingletonPage'],[])
        childmap = o.childmap()
        self.assertEquals(len(childmap.keys()),2)
        self.assertEquals(childmap['GrandChildPage'],[])
        self.assertEquals(childmap['SingletonPage'],[])

    def test_replace(self):
        o = self.outline
        self.assert_(o.hasNode('TestPage'))
        self.assert_(not o.hasNode('RenamedPage'))
        children = o.children('TestPage')
        o.replace('TestPage','RenamedPage')
        self.assert_(not o.hasNode('TestPage'))
        self.assert_(o.hasNode('RenamedPage'))
        self.assertEquals(o.children('RenamedPage'),children)

    def test_reparent(self):
        o = self.outline
        self.assertEquals(o.parents('ChildPage'),['RootPage'])
        o.reparent('ChildPage',['TestPage'])
        self.assertEquals(o.parents('ChildPage'),['TestPage'])

