# page rating support mixin

import string, re
#from types import *
#from urllib import quote, unquote

from AccessControl import ClassSecurityInfo
import Globals

import Permissions


class RatingSupport:
    """
    I manage a rating (score) for a wiki page, based on user votes.

    User votes are stored as a dictionary keyed by username/ip address.
    A user can change their vote by re-voting.
    """
    security = ClassSecurityInfo()

    _votes = None # not {}, it would be shared

    security.declarePrivate('votes')
    def votes(self):
        votes = self.aq_base._votes
        if votes is None: return {}
        else: return votes

    security.declarePrivate('setVotes')
    def setVotes(self,votes):
        self.aq_base._votes = votes
        # make sure persistence sees this - no longer needed ?
        #self._p_changed = 1
        
    security.declarePrivate('resetVotes')
    def resetVotes(self):
        self.setVotes({})

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
                try: del votes[username]
                except KeyError: pass
            else:
                votes[username] = score
            self.setVotes(votes)
            self.reindex_object() # XXX only need update votes fields
            if REQUEST: REQUEST.RESPONSE.redirect(REQUEST['URL1']+'#ratingform')

    security.declareProtected(Permissions.View, 'voteCount')
    def voteCount(self):
        """
        How many users have voted on this page since last reset ?
        """
        return len(self.votes())

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
        total = 0
        for score in self.votes().values(): total += score
        return total / (self.voteCount() or 1)
        



# install permissions
Globals.InitializeClass(RatingSupport) 
