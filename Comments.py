# CommentsSupport mixin
# related to Mail.py

import sys, os, string, re, email, email.Errors
from mailbox import UnixMailbox, PortableUnixMailbox
from urllib import quote
from cStringIO import StringIO

from App.Common import absattr
from DateTime import DateTime
from AccessControl import getSecurityManager, ClassSecurityInfo

import Permissions
from Utils import BLATHER, html_quote, DateTimeSyntaxError, \
  stringBefore, stringBeforeAndIncluding, stringAfter, stringAfterAndIncluding
from Regexps import fromlineexpr


class CommentsSupport:
    """
    This mix-in class handles comments stored as rfc2822 messages in the page.

    This class looks for comments in mbox/RFC2822 format in the page text,
    and provides services for parsing and displaying them.  Everything
    above the first comment is considered the document part, the rest of
    the page is considered the discussion part.

    Prior to 0.30 we called these Messages; you may see references to both.

    So that we can recognize comments/messages without extra markup or too
    many false positives, we require each message to begin with BAW's "strict"
    From line regexp from the python mailbox module.

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
        Return the messages on this page as an iterator of Message objects.
        """
        # UnixMailbox(/rfc822 ?) doesn't like unicode.. work around for now.
        # NB at present unicode may get added:
        # - via user edit
        # - when a comment is posted and the local timezone contains unicode
        # - when rename writes a placeholder page (because of the use of _() !)
        #try:
        #    return UnixMailbox(StringIO(self.text()))
        #except TypeError:
        #    BLATHER(self.id(),'contains unicode, could not parse comments')
        #    #BLATHER(repr(self.text()))
        #    return UnixMailbox(StringIO(''))

        # mailbox docs: this is defensive against ill-formed MIME messages
        # in the mailbox, but you have to be prepared to receive the empty
        # string from the mailbox's `next()' method
        def msgfactory(fp):
            try:
                return email.message_from_file(fp)
            except email.Errors.MessageParseError:
                BLATHER('message parsing error in',self.id())
                return ''
        return UnixMailbox(StringIO(self.text()), msgfactory)

    def comments(self):
        """
        Return this page's comments as a list of Messages.
        """
        msgs = []
        mbox = self.mailbox()
        m = mbox.next()
        while m is not None:
            msgs.append(m)
            m = mbox.next()
        return msgs


    # utilities

    def makeMessageFrom(self,From,time,message_id,
                        subject='',in_reply_to=None,body=''):
        """
        Create a nice RFC2822-format message to store in the page.
        """
        msg = """\
%s
From: %s
Date: %s
Subject: %s
Message-ID: %s
""" % (self.fromLineFrom(From,time)[:-1],From,time,subject,message_id)
        if in_reply_to:
            msg += 'In-reply-to: %s\n' % in_reply_to
        msg += '\n'+body
        return msg

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

    security.declareProtected(Permissions.View, 'upgradeComments')
    def upgradeComments(self,REQUEST=None):
        """
        Update the format of any comments on this page.
        """
        # XXX upgrade old-style zwiki comments to mbox-style messages ?
        pass

        # add proper From delimiters
        # XXX that's a bit aggressive and is no longer needed I think
        if re.search(r'\n\nFrom: ',self.text()):
            msgs = ''
            mailbox = PortableUnixMailbox(StringIO(
                re.sub(r'\n\nFrom: ',r'\n\nFrom \nFrom: ',self.text())))
            m = mailbox.next()
            while m is not None:
                msgs += self.fromLineFrom(m.get('from'),m.get('date'))
                msgs += string.join(m.headers,'')
                msgs += '\n'
                msgs += m.fp.read()
                m = mailbox.next()
            new = re.split('\n\nFrom: ',self.text(),1)[0]+'\n\n'+msgs
            self.edit(text=new, REQUEST=REQUEST,log='upgraded comments')
            BLATHER('upgraded comments on',self.id())

    # backwards compatibility
    supportsMessages = supportsComments
    hasMessages = hasComments
    messageCount = commentCount
    messagesPart = discussionPart
    messages = comments
    upgradeMessages = upgradeComments

