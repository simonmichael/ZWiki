# Messages mixin 

import sys, os, string, re, rfc822
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


class MessagesSupport:
    """
    This mix-in class handles comments stored as rfc2822 messages in the page.

    This class looks for messages in the page text, in mbox/RFC2822
    format, and provides services for parsing and displaying them.
    Everything above the first message is considered the document part,
    the rest of the page is considered the messages part.

    So that we can recognize messages without extra markup or too many
    false positives, we require each message to begin with BAW's "strict"
    From line regexp from the python mailbox module.

    """
    security = ClassSecurityInfo()

    security.declareProtected(Permissions.View, 'supportsMessages')
    def supportsMessages(self):
        """does this page parse embedded rfc822-ish messages ?"""
        return re.search(r'(?i)(msg)',self.pageTypeId()) is not None

    security.declareProtected(Permissions.View, 'mailbox')
    def mailbox(self):
        """
        Return the messages on this page as an iterator of rfc822.Message.
        """
        # XXX UnixMailbox doesn't like unicode.. work around for now.
        # NB at present unicode may get added:
        # - via user edit
        # - when a message is posted and the local timezone contains unicode
        # - when rename writes a placeholder page (because of the use of _() !)
        try:
            return UnixMailbox(StringIO(self.text()))
        except TypeError:
            BLATHER(self.id(),'contains unicode, could not parse messages')
            #BLATHER(repr(self.text()))
            return UnixMailbox(StringIO(''))

    def messages(self):
        """
        Return this page's messages as a list of rfc822.Message.
        """
        msgs = []
        mbox = self.mailbox()
        m = mbox.next()
        while m is not None:
            msgs.append(m)
            m = mbox.next()
        return msgs

    security.declareProtected(Permissions.View, 'hasMessages')
    def hasMessages(self):
        """does this page have one or more embedded rfc822-ish messages ?"""
        return self.messageCount() > 0

    security.declareProtected(Permissions.View, 'messageCount')
    def messageCount(self):
        """
        The number of messages in this page.
        """
        return len(re.findall(fromlineexpr,self.messagesPart()))

    security.declareProtected(Permissions.View, 'documentPart')
    def documentPart(self):
        """
        This page's text from beginning up to the first message, if any.
        """
        return re.split(fromlineexpr,self.text(),1)[0]

    document = documentPart

    security.declareProtected(Permissions.View, 'messagesPart')
    def messagesPart(self):
        """
        This page's text from the first message to the end (or '').
        """
        return stringAfterAndIncluding(fromlineexpr,self.text())

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

    security.declareProtected(Permissions.View, 'upgradeMessages')
    def upgradeMessages(self,REQUEST=None):
        """
        Update the format of any messages on this page.
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
            self.edit(text=new, REQUEST=REQUEST,log='upgraded messages')
            BLATHER('upgraded messages on',self.id())

