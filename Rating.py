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

    security.declareProtected(Permissions.View, 'rating')
    def rating(self):
        """
        Get this page's rating (an integer).
        """
        pass

    security.declareProtected(Permissions.View, 'resetRating')
    def resetRating(self):
        """
        Reset this page's rating to the default value.
        """
        pass

    security.declareProtected(Permissions.View, 'rate')
    def rate(self,score,REQUEST=None):
        """
        Update this page's rating based on a user's vote.
        """
        pass


# install permissions
Globals.InitializeClass(RatingSupport) 
