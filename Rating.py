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
    """
    security = ClassSecurityInfo()

    _rating = 0

    def setRating(self,score): self._rating = score

    def resetRating(self): self.setRating(0)

    security.declareProtected(Permissions.View, 'rating')
    def rating(self):
        """
        Get this page's rating (an integer).
        """
        return self._rating

    security.declareProtected(Permissions.View, 'rate')
    def rate(self,score,REQUEST=None):
        """
        Update this page's rating based on a user's vote.
        """
        self.setRating(score)


# install permissions
Globals.InitializeClass(RatingSupport) 
