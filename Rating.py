# page rating support mixin

import string, re
#from types import *
#from urllib import quote, unquote

from AccessControl import ClassSecurityInfo
import Globals

import Permissions
from Utils import BLATHER
from UI import loadPageTemplate, onlyBodyFrom, DEFAULT_TEMPLATES

DEFAULT_TEMPLATES['ratingform'] = loadPageTemplate('ratingform')


class RatingSupport:
    """
    I manage a numeric rating based on user votes.

    Votes are stored as a dictionary keyed by username/ip address.
    A user can change their vote by re-voting, or cancel their vote.
    """
    security = ClassSecurityInfo()

    _votes = None # not {}, it would be shared

    security.declarePrivate('votes')
    def votes(self): return self.aq_base._votes or {}

    security.declarePrivate('setVotes')
    def setVotes(self,votes): self.aq_base._votes = votes
        
    security.declarePrivate('resetVotes')
    def resetVotes(self): self.setVotes({})

    # api methods
    
    security.declareProtected(Permissions.Rate, 'rate')
    def vote(self,score=None,REQUEST=None):
        """
        Record a user's vote for this page (or unrecord it).
        """
        username = self.usernameFrom(REQUEST)
        if username:
            votes = self.votes()
            if score is None:
                try:
                    del votes[username]
                    BLATHER("%s: removed %s's vote" % (self.pageName(),username))
                except KeyError: pass
            else:
                votes[username] = score
                BLATHER("%s: recorded %s vote for %s" % (self.pageName(),score,username))
            self.setVotes(votes)
            self.reindex_object() # XXX only need update votes fields
            if REQUEST: REQUEST.RESPONSE.redirect(REQUEST['URL1']+'#ratingform')

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
        What is the user's current rating for this page ? May be None.
        """
        return self.votes().get(self.usernameFrom(REQUEST),None)

    security.declareProtected(Permissions.View, 'rating')
    def rating(self):
        """
        Get this page's average rating (an integer).
        """
        if self.hasVotes(): return sum(self.votes().values())/self.voteCount()
        else: return 0

    security.declareProtected(Permissions.View, 'ratingform')
    def ratingform(self, REQUEST=None):
        """
        Render the page rating form as a (customizable) HTML fragment.

        The page's rating, current user's vote etc. will be highlighted.
        """
        return onlyBodyFrom(
            self.getSkinTemplate('ratingform')(self,REQUEST)
            )


# install permissions
Globals.InitializeClass(RatingSupport) 
