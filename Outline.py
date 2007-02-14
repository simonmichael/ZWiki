# zwiki Outline class (page hierarchy helper)
from __future__ import nested_scopes
from types import *

class Outline:
    """
    I represent and answer questions about a multi-root, multi-parent
    hierarchy of objects, usually strings, efficiently.

    This is based on Ken Manheimer's WikiNesting enhancement.
    For the moment, an Outline has
      _parentmap = {'Root':[],'Child':['Root'],'GrandChild':['Child'],'Single':[]}
      _childmap =  {'Root':['Child'],'Child':['GrandChild'],'GrandChild':[],'Single':[]}
      _nesting =   [['Root',['Child','GrandChild']],'Single']
    A nesting represents outline nodes as follows:
      Leaves: the string name of the page
      Nodes with children: a list beginning with the parent node's name
      Nodes with omitted children (for brevity): list with one string.
    _childmap and _nesting are derived from _parentmap.
    Outlines and nestings should perhaps be the same thing.

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
    def updateChildmap(self,reset=0):
        """Regenerate childmap from parentmap.

        childmap is the inverse of parentmap - except, it remembers any
        manual re-ordering of children. Unless reset is true we try to
        preserve the order of children, which complicates things badly.
        """
        nodes = self.nodes()
        # XXX still problems with things not getting updated properly
        oldchildmap = self.childmap()
        if reset:
            childmap = {}
        else:
            # backwards compatibility: 0.39 might have set this to None
            childmap = self.childmap() or {} 
            # remove any no-longer-existing nodes from childmap
            for p in childmap.keys()[:]:
                if not p in nodes: del childmap[p]
                else:
                    for c in childmap[p][:]: # a copy
                        if not c in nodes: childmap[p].remove(c)
        # make sure each existing node appears in the childmap
        for c in nodes:
            for p in self.parents(c):
                # each parent should have a childmap entry including this child
                if not childmap.has_key(p): childmap[p] = [c]
                elif not c in childmap[p]: childmap[p].append(c)
        # add a childmap entry for any nodes we missed (non-parents)
        for l in filter(lambda x:x not in childmap.keys(),nodes):
            childmap[l] = []
        self.setChildmap(childmap)
    def updateNesting(self):
        """Regenerate nesting from childmap and roots."""
        self.setNesting(self.offspring(self.roots()))
    def update(self):
        """Regenerate everything from the parentmap."""
        self.updateChildmap()
        self.updateNesting()
    def __init__(self,parentmap={}):
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

        If node wasn't there, just add newnode. This is useful for rename().
        Should this sort of robustness check be done here or there ?

        Tries to preserve node's ordering among it's siblings, as in
        updateChildMap.
        """
        parentmap = self.parentmap()
        # replace node with newnode, preserving node's parents
        parents = self.parents(node)
        if parentmap.has_key(node): del parentmap[node]
        parentmap[newnode] = parents
        # reparent node's children under newnode
        for c in filter(lambda x:node in parentmap[x],parentmap.keys()):
            parentmap[c].remove(node)
            parentmap[c].append(newnode)
        self.setParentmap(parentmap)

        # tweak childmap before updateChildMap, to preserve node's position
        childmap = self.childmap()
        for p in childmap.keys():
            if node in childmap[p]:
                childmap[p][childmap[p].index(node)] = newnode
        self.setChildmap(childmap)

        if update: self.update()
    def reparent(self,node,newparents,update=1):
        """
        Change node's parents to newparents in the outline.
        """
        # help prepare childmap for updateChildMap 
        childmap = self.childmap()
        for p in self.parents(node): childmap[p].remove(node)
        self.setChildmap(childmap)
            
        self.add(node,newparents,update)
    def reorder(self,node,child):
        """
        Moves child one place to the left among node's children (in _childmap).
        """
        childmap = self.childmap()
        #we do no error checking in this class IIRC
        #if not childmap.has_key(node): return
        children = childmap[node]
        #if not child in children: return
        i = children.index(child)
        #if not i: return
        children[i-1], children[i] = children[i], children[i-1]
        childmap[node] = children
        self.setChildmap(childmap)
        self.updateNesting()
    def first(self):
        """
        Get the first node in the outline.
        """
        list = self.flat()
        if list: return list[0]
        else: return None
    def last(self):
        """
        Get the last node in the outline.
        """
        list = self.flat()
        if list: return list[-1]
        else: return None
    def next(self,node,wrap=0):
        """
        Get the next node in the outline.
        """
        list = self.flat()
        if node in list:
            i = list.index(node)
            if i < len(list)-1: return list[i+1]
            elif wrap: return list[0]
        return None
    def previous(self,node,wrap=0):
        """
        Get the previous node in the outline.
        """
        list = self.flat()
        if node in list:
            i = list.index(node)
            if i > 0: return list[i-1]
            elif wrap: return list[-1]
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
    def parents(self,node=None):
        """
        Return a nesting/list representing node's immediate parents.
        """
        #XXX temporary nasty kludge: there seems no obvious way to prevent
        #zcatalog from trying to index this object, calling any methods
        #which (like this one) match catalog index names, when a user does
        #find all objects. So don't break when that happens.
        if not node: return None
        return self.parentmap().get(node,[])[:]
            
    def firstParent(self,node):
        """
        Return the first parent of node, if any.
        """
        parents = self.parentmap().get(node,None)
        if parents: return parents[0]
        else: return None
    def siblings(self,node,include_me=False,sort_alpha=True): 
        """
        Return a nesting/list representing node's siblings.

        Ie, any other children of node's first parent. Any siblings by the
        other parents are not included.
        Optionally include the current page (node) in the list.
        Optionally suppress alphabetical sorting of result.
        """
        parent = self.firstParent(node)
        sibs = self.children(parent)
        if not include_me:
            sibs.remove(node)
        if sort_alpha:
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
    def offspring(self,nodes,did=None,depth=None):
        """
        Return a nesting representing all descendants of all specified nodes.

        nodes is a list of nodes; these will be included in the nesting.
        did is used only for recursion.

        If depth is specified, descendendants beyond that depth will be
        ignored.
        XXX this is better done in the view layer, remove it.
        
        """
        if did is None: did = {}
        got = []
        for n in nodes:
            been_there = did.has_key(n)
            did[n] = None
            if self.childmap().has_key(n) and not depth==0:
                children = self.childmap()[n]
                if children:
                    subgot = [n]
                    if not been_there:
                        subgot.extend(
                            self.offspring(children,
                                           depth=(depth and depth-1),
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

# copied from Utils to avoid zope dependencies
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

