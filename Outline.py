# zwiki Outline class (page hierarchy helper)
from __future__ import nested_scopes
from types import *

class Outline:
    """
    I represent and answer questions about a multi-root, multi-parent
    hierarchy of objects, usually strings, efficiently.

    For the moment, an Outline has
      _parentmap = {'Root':[],'Child':['Root'],'GrandChild':['Child'],'Single':[]}
      _childmap =  {'Root':['Child'],'Child':['GrandChild'],'GrandChild':[],'Single':[]}
      _nesting =   [['Root',['Child','GrandChild']],'Single']
    A nesting represents outline nodes as follows:
      Leaves: the string name of the page
      Nodes with children: a list beginning with the parent node's name
      Nodes with omitted children (for brevity): list with one string.
    This is based on Ken Manheimer's WikiNesting implementation for Zwiki.
    Outlines and nestings should perhaps be the same thing.
    childmap is the inverse of parentmap.

    """
    _parentmap = {}
    _childmap =  {}
    _nesting =   []
    def parentmap(self): return self._parentmap
    def setParentmap(self,parentmap): self._parentmap = parentmap
    def childmap(self): return self._childmap
    def setChildmap(self,childmap): self._childmap = childmap
    def nesting(self): return self._nesting
    def setNesting(self,nesting): self._nesting = nesting
    def nodes(self):
        """Return a sorted list of all nodes."""
        nodes = self.parentmap().keys()
        nodes.sort()
        return nodes
    def nodeCount(self): return len(self.nodes())
    def hasNode(self,node): return node in self.nodes()
    def flat(self):
        """Return a flattened version of the outline, preserving order."""
        return flatten(self.nesting())
    def roots(self):
        """Return a sorted list of the root nodes."""
        return filter(lambda x:not self.parents(x), self.nodes())
    def leaves(self):
        """Return a sorted list of the leaf nodes."""
        return filter(lambda x:not self.children(x), self.nodes())
    def updateChildmap(self):
        """Regenerate childmap from parentmap."""
        childmap = {}
        for c in self.nodes():
            parents = self.parents(c)
            for p in parents:
                if not childmap.has_key(p): childmap[p] = [c]
                else: childmap[p].append(c)
        for l in filter(lambda x:x not in childmap.keys(),self.nodes()):
            childmap[l] = []
        self.setChildmap(childmap)
    def updateNesting(self):
        """Regenerate nesting from childmap and roots."""
        self.setNesting(self.offspring(self.roots()))
    def update(self):
        """Regenerate everything from the parentmap."""
        self.updateChildmap()
        self.updateNesting()
    def __init__(self,parentmap):
        self.setParentmap(parentmap)
        self.update()
    def add(self,node,parents=[],update=1):
        """
        Add node to the outline, under the specified parents if any.

        If node is already present, it will be reparented.
        """
        parentmap = self.parentmap()
        parentmap[node] = parents[:] # use a copy
        self.setParentmap(parentmap)
        if update: self.update()
    def delete(self,node,update=1):
        """
        Remove node from the outline.
        """
        for c in self.children(node):
            self.reparent(c,self.parents(node),update=0)
        parentmap = self.parentmap()
        del parentmap[node]
        self.setParentmap(parentmap)
        if update: self.update()
    def replace(self,node,newnode,update=1):
        """
        Replace node with newnode in the outline.
        """
        parentmap = self.parentmap()
        # replace node with newnode, preserving node's parents
        parents = self.parents(node)
        del parentmap[node]
        parentmap[newnode] = parents
        # reparent node's children under newnode
        for c in filter(lambda x:node in parentmap[x],parentmap.keys()):
            parentmap[c].remove(node)
            parentmap[c].append(newnode)
        self.setParentmap(parentmap)
        if update: self.update()
    def reparent(self,node,newparents,update=1):
        """
        Change node's parents to newparents in the outline.
        """
        self.add(node,newparents,update)
    def next(self,node):
        list = self.flat()
        if node in list:
            i = list.index(node)
            if i < len(list)-1: return list[i+1]
        return None
    def previous(self,node):
        list = self.flat()
        if node in list:
            i = list.index(node)
            if i > 0: return list[i-1]
        return None
    def ancestors(self,node):
        """
        Return a nesting representing the ancestors of the specified node.

        node itself is included.
        """
        ancestors = {}
        tops = {}
        offspring = {}
        todo = {node: None}
        # Go up, identifying all and topmost forebears:
        while todo:
            doing = todo
            todo = {}
            for n in doing.keys():
                if ancestors.has_key(n): continue # already collected this one
                else:
                    ancestors[n] = None
                    parents = self.parents(n)
                    if parents:
                        for p in parents:
                            if offspring.has_key(p): offspring[p].append(n)
                            else: offspring[p] = [n]
                            todo[p] = None
                    else:
                        tops[n] = None
        # Ok, now go back down, unravelling each forebear only once:
        tops = tops.keys()
        tops.sort
        did = {}; got = []
        for t in tops:
            got.append(descend_ancestors(t, ancestors, did, offspring))
        return got
    def ancestorsAndSiblings(self,node):
        """
        Return a nesting representing the ancestors and siblings of node.
        """
        ancestors = {}
        tops = {}
        offspring = {}
        todo = {node: None}
        # Go up, identifying all and topmost forebears:
        while todo:
            doing = todo
            todo = {}
            for n in doing.keys():
                if ancestors.has_key(n): continue
                else:
                    ancestors[n] = None
                    parents = self.parents(n)
                    if parents:
                        for p in parents:
                            if p != n:
                                if offspring.has_key(p): offspring[p].append(n)
                                else: offspring[p] = [n]
                            todo[p] = None
                    else:
                        tops[n] = None
        # Ok, now go back down, unravelling each forebear only once:
        tops = tops.keys()
        tops.sort
        did = {}; got = []
        for t in tops:
            if t == node: got.append([t])
            else:
                got.append(descend_ancestors(t,ancestors,did,offspring))
        return got
    def ancestorsAndChildren(self,node):
        """
        Return a nesting representing the ancestors and children of node.
        """
        # Go up, identifying all and topmost forebears:
        ancestors = {}
        tops = {}     
        todo = {node: None}
        while todo:
            doing = todo
            todo = {}
            for n in doing.keys():
                if ancestors.has_key(n): continue
                else:
                    ancestors[n] = None
                    parents = self.parents(n)
                    if parents:
                        for p in parents:
                            todo[p] = None
                    else: tops[n] = None
        ancestors[node] = None      # Finesse inclusion of page's offspring
        # Ok, now go back down, showing offspring of all intervening ancestors:
        tops = tops.keys()
        tops.sort
        did = {}; got = []
        for t in tops:
            got.append(descend_ancestors(t, ancestors, did, self.childmap()))
        return got
    def parents(self,node):
        """
        Return a nesting/list representing node's immediate parents.
        """
        return self.parentmap()[node][:]
    def firstParent(self,node):
        """
        Return the first parent of node, if any.
        """
        parents = self.parentmap()[node]
        if parents: return parents[0]
        else: return None
    def siblings(self,node): 
        """
        Return a nesting/list representing node's siblings.

        Ie, any other children of node's first parent. Any siblings by the
        other parents are not included.
        """
        parent = self.firstParent(node)
        sibs = self.children(parent)
        sibs.remove(node)
        sibs.sort()
        return sibs
    def children(self,node=None):
        """
        Return a nesting/list representing node's immediate children.

        If node is None or [], return the roots.
        """
        if self.hasNode(node): return self.childmap()[node][:]
        elif not node: return self.roots()
        else: return []
    def offspring(self,nodes,did=None):
        """
        Return a nesting representing all descendants of all specified nodes.

        nodes is a list of nodes; these will be included in the nesting.
        did is used only for recursion.
        """
        if did is None: did = {}
        got = []
        for n in nodes:
            been_there = did.has_key(n)
            did[n] = None
            if self.childmap().has_key(n):
                children = self.childmap()[n]
                if children:
                    subgot = [n]
                    if not been_there:
                        subgot.extend(self.offspring(children,
                                                     did=did))
                    got.append(subgot)
                else:
                    got.append(n)
            else:
                got.append(n)
        return got

# helper functions

def descend_ancestors(page, ancestors, did, children):
    """
    Create nesting of ancestors leading to page.

    page is the name of the subject page.
    ancestors is a mapping whose keys are pages that are ancestors of page
    children is a mapping whose keys are pages children, and the values
       are the children's parents.

    Do not repeat ones we already did.
    """
    got = []
    for c in ((children.has_key(page) and children[page]) or []):
        if not ancestors.has_key(c):
            # We don't descend offspring that are not ancestors.
            got.append(c)
        elif ((children.has_key(c) and children[c]) or []):
            if did.has_key(c):
                # We only show offspring of ancestors once...
                got.append([c])
            else:
                # ... and this is the first time.
                did[c] = None
                got.append(descend_ancestors(c, ancestors, did, children))
        else:
            got.append(c)
    got.sort()                  # Terminals will come before composites.
    got.insert(0, page)
    return got

# copied from ZWiki.Utils to avoid zope dependencies
def flatten(recursiveList):
    """
    Flatten a recursive list/tuple structure.
    """
    flatList = []
    for i in recursiveList:
        if type(i) in (ListType,TupleType): flatList.extend(flatten(list(i)))
        else: flatList.append(i)
    return flatList

flatten2 = lambda l,f=lambda L,F : type(L) != type([]) and [L] or reduce(lambda a,b,F=F : a + F(b,F), L, []) :f(l,f)

