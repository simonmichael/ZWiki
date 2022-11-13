# PageCommentsSupport mixin

import sys, os, string, re, email, email.Errors
from mailbox import UnixMailbox
from urllib import quote
from cStringIO import StringIO

from AccessControl import getSecurityManager, ClassSecurityInfo
from App.Common import absattr
from DateTime import DateTime
from AccessControl.class_init import InitializeClass

import Permissions
from Regexps import fromlineexpr
from Utils import BLATHER, html_quote, DateTimeSyntaxError, \
  stringBefore, stringBeforeAndIncluding, stringAfter, \
  stringAfterAndIncluding, safe_hasattr


class PageCommentsSupport:
    """
    I manage comments stored as rfc2822 messages in a wiki page.

    This mixin class looks for comments in mbox/RFC2822 format in the page
    text, and provides services for parsing and displaying them.
    Everything above the first comment is considered the document part,
    the rest of the page is considered the discussion part.

    Prior to 0.30 we called this MessageSupport. When working with
    comments, we represent them as email.Message.Message objects.

    So that we can recognize comments/messages without extra markup or too
    many false positives, we require each message to begin with BAW's "strict"
    From line regexp from the python mailbox module.

    See also Editing.py.
    """
    security = ClassSecurityInfo()

    # accessors

    security.declareProtected(Permissions.View, 'supportsComments')
    def supportsComments(self):
        """does this page parse embedded rfc2822 messages ?"""
        return re.search(r'(?i)(msg)',self.pageTypeId()) is not None

    security.declareProtected(Permissions.View, 'hasComments')
    def hasComments(self):
        """does this page have one or more rfc2822-style comments ?"""
        return self.messageCount() > 0

    security.declareProtected(Permissions.View, 'commentCount')
    def commentCount(self):
        """
        The number of comments in this page.
        """
        return len(re.findall(fromlineexpr,self.discussionPart()))

    security.declareProtected(Permissions.View, 'documentPart')
    def documentPart(self):
        """
        This page's text from beginning up to the first message, if any.
        """
        return re.split(fromlineexpr,self.text(),1)[0]

    document = documentPart

    security.declareProtected(Permissions.View, 'discussionPart')
    def discussionPart(self):
        """
        This page's text from the first comment to the end (or '').
        """
        return stringAfterAndIncluding(fromlineexpr,self.text())

    security.declareProtected(Permissions.View, 'mailbox')
    def mailbox(self):
        """
        Return the messages on this page as a Mailbox (iterator of Message)
        """
        # from mailbox docs: this is defensive against ill-formed MIME
        # messages in the mailbox, but you have to be prepared to receive
        # the empty string from the mailbox's `next()' method
        def msgfactory(fp):
            try:
                return email.message_from_file(fp)
            except email.Errors.MessageParseError:
                BLATHER('message parsing error in',self.id())
                return ''
        return UnixMailbox(StringIO(self.toencoded(self.text())), msgfactory)

    def comments(self):
        """
        Return this page's comments as a list of email Messages.

        Warning, the email lib's Messages contain encoded text and you
        must remember to convert their data to unicode when
        appropriate.
        """
        msgs = []
        mbox = self.mailbox()
        m = mbox.next()
        while m is not None:
            msgs.append(m)
            m = mbox.next()
        return msgs


    # utilities

    def fromLineFrom(self,email,date):
        """
        Generate a conformant mbox From line from email and date strings.

        (unless date is unparseable, in which case we omit that part)
        """
        # "email" is in fact a real name or zwiki username - adapt it
        email = re.sub(r'\s','',email) or 'unknown'
        try:
            d = DateTime(date)
            return 'From %s %s %s %d %02d:%02d:%02d %s %d\n' % (
                email,d.aDay(),d.aMonth(),d.day(),d.hour(),
                d.minute(),d.second(),d.timezone(),d.year())
        except (DateTimeSyntaxError,AttributeError,IndexError):
            return 'From %s\n' % email

    def messageIdFromTime(self,time):
        """
        Generate a somewhat unique email message-id based on a DateTime
        """
        msgid = time.strftime('%Y%m%d%H%M%S')+time.rfc822()[-5:]+'@'
        if safe_hasattr(self,'REQUEST'):
            msgid += re.sub(r'http://','',self.REQUEST.get('SERVER_URL',''))
        msgid = '<%s>' % msgid
        return msgid

    security.declareProtected(Permissions.View, 'upgradeComments')
    def upgradeComments(self,REQUEST=None):
        """Update the format of any comments on this page."""
        pass # all current zwikis use the rfc2822 format

    # backwards compatibility
    supportsMessages = supportsComments
    hasMessages = hasComments
    messageCount = commentCount
    messagesPart = discussionPart
    messages = comments
    upgradeMessages = upgradeComments

InitializeClass(PageCommentsSupport)

