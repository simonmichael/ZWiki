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

    _votes = {}

    def clearVotes(self):
        self._votes = {}
        self.reindex_object() # XXX votes field only

    security.declareProtected(Permissions.Rate, 'rate')
    def vote(self,score=None,REQUEST=None):
        """
        Record a user's vote for this page.
        """
        username = self.usernameFrom(REQUEST)
        if username:
            self._votes[username] = score
            # make sure persistence sees this
            self._p_changed = 1
            self.reindex_object() # XXX votes field only
            if REQUEST: REQUEST.RESPONSE.redirect(REQUEST['URL1']+'#ratingform')

    security.declareProtected(Permissions.View, 'voteCount')
    def voteCount(self):
        """
        How many users have voted on this page since last reset ?
        """
        return len(self._votes.keys())

    security.declareProtected(Permissions.View, 'myVote')
    def myVote(self,REQUEST=None):
        """
        What is the user's current rating for this page ? May be None.
        """
        return self._votes.get(self.usernameFrom(REQUEST),None)

    security.declareProtected(Permissions.View, 'rating')
    def rating(self):
        """
        Get this page's average rating (an integer).
        """
        total = 0
        for score in self._votes.values(): total += score
        return total / (self.voteCount() or 1)
        


# install permissions
Globals.InitializeClass(RatingSupport) 
