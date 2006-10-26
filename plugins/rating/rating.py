# page rating support mixin

import string, re
#from types import *
#from urllib import quote, unquote

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Products.ZWiki.plugins import registerPlugin
from Products.ZWiki.Defaults import registerPageMetaData
from Products.ZWiki import Permissions
from Products.ZWiki.Utils import BLATHER
from Products.ZWiki.Views import loadPageTemplate, TEMPLATES

TEMPLATES['ratingform'] = loadPageTemplate('ratingform','plugins/rating')

RATING_METADATA = [
    'voteCount',
    'rating',
    ]
for a in RATING_METADATA: registerPageMetaData(a)


class PluginRating:
    """
    I am a mixin that manages a numeric rating based on user votes.

    Votes are stored as a dictionary keyed by username/ip address.
    A user can change their vote by re-voting, or cancel their vote.

    In theory at least, votes are strings.  The rating method interprets
    votes as numbers and returns the average.
    """
    security = ClassSecurityInfo()

    _votes = None # not {}, it would be shared

    security.declarePrivate('votes')
    def votes(self):
        """Private accessor."""
        self = getattr(self,'aq_base',self)
        return self._votes or {}

    security.declarePrivate('setVotes')
    def setVotes(self,votes):
        """Private accessor."""
        self = getattr(self,'aq_base',self)
        self._votes = votes
        
    security.declarePrivate('resetVotes')
    def resetVotes(self):
        """Private accessor."""
        self.setVotes({})

    security.declarePublic('numericVotes') # XXX better name ?
    def numericVotes(self):
        """Get just the numeric votes without the usernames."""
        return self.votes().values()

    # api methods
    
    security.declareProtected(Permissions.Rate, 'vote')
    def vote(self,vote=None,REQUEST=None):
        """
        Record a user's vote for this page (or unrecord it).

        To help build robust image-button forms, if vote is None, also
        look for form values named like vote0, vote1.. voteN and use N.
        """
        username = self.usernameFrom(REQUEST)
        if username:
            votes = self.votes()
            if vote == None:
                # look for a form input named voteN and get N
                # depending on browser, there will also be
                # voteN.x and voteN.y, or only these
                if REQUEST:
                    votefields = [k for k in REQUEST.form.keys()
                                  if k.startswith('vote')]
                    if votefields:
                        vote = votefields[0][4:]
                        vote = re.sub(r'\.[xy]$','',vote)
            if vote == None:
                try:
                    del votes[username]
                    BLATHER("%s: removed %s's vote" % (self.pageName(),username))
                except KeyError: pass
            else:
                votes[username] = vote
                BLATHER("%s: recorded %s vote for %s" % (self.pageName(),vote,username))
            self.setVotes(votes)
            self.index_object() # XXX only need update votes fields
            if REQUEST:
                REQUEST.RESPONSE.redirect(
                    # redirect to the page they came on.. might be some
                    # other page, eg a list of rated pages. Is this robust ?
                    #REQUEST.URL1
                    REQUEST.HTTP_REFERER
                    )

    security.declareProtected(Permissions.Rate, 'unvote')
    def unvote(self,REQUEST=None):
        """
        Unrecord a user's vote for this page.
        """
        return self.vote(None,REQUEST)

    security.declareProtected(Permissions.View, 'voteCount')
    def voteCount(self):
        """
        How many users have voted on this page since last reset ?
        """
        return len(self.votes())

    security.declareProtected(Permissions.View, 'hasVotes')
    def hasVotes(self): return self.voteCount() > 0
        
    security.declareProtected(Permissions.View, 'myVote')
    def myVote(self,REQUEST=None):
        """
        What is the current user's recorded vote for this page ? 

        Returns a string or None.
        """
        return self.votes().get(self.usernameFrom(REQUEST),None)

    security.declareProtected(Permissions.View, 'myVotes')
    def myVotes(self,REQUEST=None):
        """
        What votes have I recorded throughout the wiki ?

        Returns a dictionary of page name:vote string pairs.
        """
        REQUEST = REQUEST or self.REQUEST
        username = self.usernameFrom(REQUEST)
        d = {}
        d.update(
            [(p.pageName(), p.votes().get(username,None))
             for p in self.pageObjects()
             if username in p.votes().keys()])
        return d

    # XXX
    security.declareProtected(Permissions.View, 'myvotes')
    def myvotes(self):
        """
        A temporary web view for the above. 
        """
        votes = self.myVotes()
        return '<pre>%s</pre>' % (
            ''.join(['%2s %s\n' % (votes[p], self.renderLinkToPage(p))
                    for p in votes.keys()]))
        
    security.declareProtected(Permissions.View, 'rating')
    def rating(self):
        """
        Return this page's overall rating, an integer.

        Interprets the recorded votes as numbers, as far as possible, and
        returns their average.  But if there have been no votes, returns a
        default rating of 1. This is so we can represent negative ratings
        with a standard simple five-star graphic. (New pages have 1 star,
        no stars means a bad page.)
        """
        if self.hasVotes():
            return float(sum(map(int,self.votes().values())))/self.voteCount()
        else:
            return 1

    # UI methods

    security.declareProtected(Permissions.View, 'ratingStyle')
    def ratingStyle(self,rating=''):
        """
        Return the CSS rating class for this page, or for the specified rating.
        """
        if rating == '' or rating == None: rating = self.rating()
        return ['lowrated','neutralrated','highrated'][cmp(rating,0)+1]

    security.declareProtected(Permissions.View, 'styledNumericRating')
    def styledNumericRating(self,rating=''):
        """
        A HTML fragment displaying this page's or the specified rating, styled.
        """
        if rating == '' or rating == None: rating = self.rating()
        return '<span class="%s">(%s)</span>' % (self.ratingStyle(rating),rating)

InitializeClass(PluginRating) 
registerPlugin(PluginRating)
