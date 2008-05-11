# PageMailSupport mixin

import re, sys
from types import *

from Globals import InitializeClass

from I18n import _
from TextFormatter import TextFormatter
from Utils import html_unquote,BLATHER,formattedTraceback,stripList, \
     isIpAddress,isEmailAddress,isUsername,safe_hasattr
from Defaults import AUTO_UPGRADE, PAGE_METATYPE


class PageSubscriptionSupport:
    """
    This mixin class adds subscriber management to a wiki page (and folder).

    Responsibilities: manage a list of subscribers for both this page and
    it's folder, and expose these in the ZMI; also do auto-upgrading.

    A "subscriber" is a string which may be either an email address or a
    CMF member username. A list of these is kept in the page's and/or
    folder's subscriber_list property.

    For the moment, it's still called "email" in arguments to avoid
    breaking legacy dtml (eg subscribeform).
    """
    subscriber_list = []
    _properties=(
        {'id':'subscriber_list', 'type': 'lines', 'mode': 'w'},
        )

    ## private ###########################################################

    def _getSubscribers(self, parent=0):
        """
        Return a copy of this page's subscriber list, as a list.
        
        With parent flag, manage the parent folder's subscriber list instead.
        """
        if AUTO_UPGRADE: self._upgradeSubscribers()
        if parent:
            if safe_hasattr(self.folder(),'subscriber_list'):
                return stripList(self.folder().subscriber_list)
            else:
                return []
        else:
            return list(self.subscriber_list)

    def _setSubscribers(self, subscriberlist, parent=0):
        """
        Set this page's subscriber list. 
        With parent flag, manage the parent folder's subscriber list instead.
        """
        if AUTO_UPGRADE: self._upgradeSubscribers()
        if parent:
            self.folder().subscriber_list = subscriberlist
        else:
            self.subscriber_list = subscriberlist

    def _resetSubscribers(self, parent=0):
        """
        Clear this page's subscriber list.
        With parent flag, manage the parent folder's subscriber list instead.
        """
        self._setSubscribers([],parent)

    def _upgradeSubscribers(self):
        """
        Upgrade old subscriber lists, both this page's and the folder's.

        Called as needed, ie on each access and also from ZWikiPage.upgrade()
        (set AUTO_UPGRADE=0 in Default.py to disable).
        
        XXX Lord have mercy! couldn't this be simpler
        """
        # upgrade the folder first; we'll check attributes then properties
        changed = 0
        f = self.folder().aq_base

        # migrate an old zwiki subscribers or wikifornow _subscribers attribute
        oldsubs = None
        if (safe_hasattr(f, 'subscribers') and
            type(f.subscribers) is StringType):
            if f.subscribers:
                oldsubs = re.sub(r'[ \t]+',r'',f.subscribers).split(',')
            try:
                del f.subscribers
            except KeyError:
                BLATHER('failed to delete self.folder().subscribers')
            changed = 1
        elif safe_hasattr(f, '_subscribers'):
            oldsubs = f._subscribers.keys()
            try:
                del f._subscribers
            except KeyError:
                BLATHER('failed to delete self.folder()._subscribers')
            changed = 1
        # ensure a subscriber_list attribute
        if not safe_hasattr(f, 'subscriber_list'): f.subscriber_list = []
        # transfer old subscribers to subscriber_list, unless it's already
        # populated in which case discard them
        if oldsubs and not f.subscriber_list: f.subscriber_list = oldsubs

        # update _properties
        props = map(lambda x:x['id'], f._properties)
        if 'subscribers' in props:
            f._properties = filter(lambda x:x['id'] != 'subscribers',
                                   f._properties)
            changed = 1
        if not 'subscriber_list' in props:
            f._properties = f._properties + \
                ({'id':'subscriber_list','type':'lines','mode':'w'},)

        if changed:
            BLATHER('upgraded %s folder subscriber list' % (f.id))

        # now do the page..
        changed = 0
        self = self.aq_base

        # migrate an old zwiki subscribers attribute
        oldsubs = None
        if (safe_hasattr(self, 'subscribers') and
            type(self.subscribers) is StringType):
            if self.subscribers:
                oldsubs = re.sub(r'[ \t]+',r'',self.subscribers).split(',')
            try:
                del self.subscribers
            except KeyError:
                BLATHER('failed to delete %s.subscribers' % (self.id()))
            changed = 1
        # copy old subscribers to subscriber_list, unless it's already
        # got some
        # XXX merge instead
        if oldsubs and not self.subscriber_list:
            self.subscriber_list = oldsubs

        # migrate a wikifornow _subscribers attribute
        oldsubs = None
        if safe_hasattr(self, '_subscribers'):
            oldsubs = self._subscribers.keys()
            try:
                del self._subscribers
            except KeyError:
                BLATHER('failed to delete %s._subscribers' % (self.id()))
            changed = 1
        if oldsubs and not self.subscriber_list:
            self.subscriber_list = oldsubs

        # update _properties
        props = map(lambda x:x['id'], self._properties)
        if 'subscribers' in props:
            self._properties = filter(lambda x:x['id'] != 'subscribers',
                                      self._properties)
            changed = 1
        if not 'subscriber_list' in props:
            self._properties = self._properties + \
                ({'id':'subscriber_list','type':'lines','mode':'w'},)

        if changed:
            BLATHER('upgraded %s subscriber list' % (self.id()))

    ## page subscription api #############################################

    # XXX rename to subscribers() & wikiSubscribers() ?
    # XXX and add editSubscribers & wikiEditSubscribers 
    def subscriberList(self, parent=0, edits=0):
        """
        Return a list of this page's subscribers, without the :edits suffix.

        A subscriber is represented by a string containing an email
        address or a CMF username, and an optional :edits suffix
        indicating they have requested all edits. Note this method strips
        the :edits suffix.

        If edits flag is true, return only the subscribers who have
        requested all edits; otherwise, return all subscribers.

        If parent flag is true, query the parent folder's subscriber list
        instead.
        """
        return [re.sub(r':edits$','',s)
                for s in stripList(self._getSubscribers(parent))
                if (not edits) or s.endswith(':edits')]

    def isSubscriber(self, email, parent=0):
        """
        Is this email address or member id subscribed to this page ?

        With parent flag, check the parent folder's subscriber list
        instead.  Note "email" may be either an email address
        (case-insensitive) or a CMF member id.  We'll accept either, and
        find subscriptions using either.
        """
        subscriber = email
        if subscriber:
            email = self.emailAddressFrom(subscriber)
            usernames = self.usernamesFrom(subscriber)
            for sub in self.subscriberList(parent):
                if not sub: continue
                if ((email and (self.emailAddressFrom(sub) == email)) or
                    (usernames and (sub in usernames))):
                    return 1
        return 0
               
    def subscribe(self, email, REQUEST=None, parent=0, edits=0):
        """
        Add an email subscriber to this page.

        subscriber may be an email address or a CMF member id.
        With parent flag, add to the parent folder's subscriber list instead.
        With edits flag, mark this subscriber as one who wants
        notification of all edits.
        """
        subscriber = email
        if subscriber:
            if not self.isSubscriber(subscriber,parent):
                BLATHER('subscribed',subscriber,'to',self.id(),
                        edits and '(all edits)' or '')
                subs = self._getSubscribers(parent)
                subs.append(subscriber + (edits and ':edits' or ''))
                self._setSubscribers(subs,parent)
                if not parent: self.index_object()
        if REQUEST:
            REQUEST.RESPONSE.redirect(
                REQUEST.get('redirectURL',
                            REQUEST['URL1']+'/subscribeform?email='+subscriber))

    def unsubscribe(self, email, REQUEST=None, parent=0):
        """
        Remove email from this page's subscriber list.

        email may be an email address or CMF username, we try to convert
        usernames to email addresses as needed.

        If parent flag is true, remove it from the parent folder's
        subscriber list instead.
        """
        subscriber = email.lower()
        if self.isSubscriber(subscriber,parent):
            sl = self._getSubscribers(parent)
            for s in sl:
                if (self.emailAddressFrom(s) ==
                    self.emailAddressFrom(subscriber)):
                    BLATHER('unsubscribed',subscriber,'from',self.id())
                    sl.remove(s)
            self._setSubscribers(sl,parent)
            if not parent: self.index_object()
        if REQUEST:
            REQUEST.RESPONSE.redirect(
                REQUEST.get('redirectURL',
                            REQUEST['URL1']+'/subscribeform?email='+subscriber))

    ## folder subscription api ###########################################

    def wikiSubscriberList(self, edits=0):
        """whole-wiki version of subscriberList"""
        return self.subscriberList(parent=1,edits=edits)

    def isWikiSubscriber(self,email):
        """whole-wiki version of isSubscriber"""
        return self.isSubscriber(email,parent=1)

    def wikiSubscribe(self, email, REQUEST=None, edits=0):
        """whole-wiki version of subscribe"""
        return self.subscribe(email,REQUEST,parent=1,edits=edits)

    def wikiUnsubscribe(self, email, REQUEST=None):
        """whole-wiki version of unsubscribe"""
        return self.unsubscribe(email,REQUEST,parent=1)

    ## misc api methods ##################################################

    def pageSubscriberCount(self, edits=0):
        """The number of subscribers to this page.  With edits flag, count only
        subscribers who have requested all edits."""
        return len(self.subscriberList(parent=0,edits=edits))

    def wikiSubscriberCount(self, edits=0):
        """The number of subscribers to the whole wiki.  With edits flag, count
        only subscribers who have requested all edits."""
        return len(self.subscriberList(parent=1,edits=edits))

    def subscriberCount(self, edits=0):
        """The total number of subscribers to this page, including wiki
        subscribers.  With edits flag, count only subscribers who have
        requested all edits."""
        return self.pageSubscriberCount(edits) + self.wikiSubscriberCount(edits)

    def subscribeThisUser(self,REQUEST):
        """
        Subscribe the current user to this page.

        We'll use their username if appropriate, otherwise their email
        address cookie.
        """
        if not REQUEST: return
        user = ((self.inCMF() and str(REQUEST.get('AUTHENTICATED_USER'))) or
                REQUEST.cookies.get('email',None))
        if user and not (self.isSubscriber(user) or self.isWikiSubscriber(user)):
            self.subscribe(user)

    def allSubscriptionsFor(self, email):
        """
        Return the ids of all pages to which a subscriber is subscribed
        ('whole_wiki' indicates a wiki subscription).

        XXX catalog case duplicates isSubscriber code
        """
        subscriber = email
        subscriptions = []
        # subscriber may be an email address or a member id, and
        # they may be subscribed as either
        email = self.emailAddressFrom(subscriber)
        usernames = self.usernamesFrom(subscriber)

        if not (email or usernames):
            return []
        if self.isWikiSubscriber(subscriber):
            subscriptions.append('whole_wiki')
        # optimization: try to use catalog for memory efficiency..
        # XXX can we do better - index subscriber_list and search
        # it directly ?
        if self.hasCatalogIndexesMetadata(
            (['meta_type','path'], ['subscriber_list'])):
            pages = self.pages()
            for page in pages:
                for sub in page.subscriber_list:
                    if not sub: continue
                    if ((email and (self.emailAddressFrom(sub) == email)) or
                        (usernames and (sub in usernames))):
                        subscriptions.append(page.id)
        else:
            # poor caching
            for id, page in self.folder().objectItems(spec=PAGE_METATYPE):
                if page.isSubscriber(subscriber):
                    subscriptions.append(id)
        return subscriptions

    def otherPageSubscriptionsFor(self, email):
        """
        Ack, this was too hard in DTML. Return the ids of all pages to
        which a subscriber is subscribed, excluding the current page and
        'whole_wiki'.
        """
        subscriber = email
        subs = self.allSubscriptionsFor(subscriber)
        thispage = self.id()
        if thispage in subs: subs.remove(thispage)
        if 'whole_wiki' in subs: subs.remove('whole_wiki')
        return subs

    def autoSubscriptionEnabled(self):
        return getattr(self,'auto_subscribe',0) and 1

    def usernameOrEmailOfSubscriber(self):
        """
        If the user is logged into the CMF, return his/her username
        else return his/her email address cookie.
        """
        if self.inCMF():
            username = str(self.portal_membership.getAuthenticatedMember())
            if username and not self.portal_membership.isAnonymousUser():
                return username
        return self.REQUEST.get('email',None)


    # utilities

    def emailAddressFrom(self,subscriber):
        """
        Convert a zwiki subscriber list entry to an email address.
        
        A zwiki subscriber list entry can be: an email address, or a CMF
        member id (if we are in a CMF/Plone site), or either of those with
        ':edits' appended.  We figure out the bare email address and
        return it (lower-cased), or if we can't, return None.
        """
        if not subscriber or type(subscriber) != StringType:
            return None
        subscriber = re.sub(r':edits$','',subscriber)
        if isEmailAddress(subscriber):
            email = subscriber
        elif self.inCMF():
            #and not self.portal_membership.isAnonymousUser()
            # don't look up member email addresses if user is anonymous ?
            # No I think it's better to minimise confusion due to
            # authenticated vs. unauthenticated (un)subscriptions, even if
            # it allows an anonymous visitor to unsubscribe a member whose
            # address they know
            from Products.CMFCore.utils import getToolByName
            membership = getToolByName(self,'portal_membership')
            memberdata = getToolByName(self,'portal_memberdata')
            member = membership.getMemberById(subscriber)
            if not member:
                # also check for a pseudo-member (a user acquired from above)
                # NB doesn't work with CMFMember
                if safe_hasattr(memberdata,'_members'):
                    member = memberdata._members.get(subscriber,None)
            # dumb robust fix for http://zwiki.org/1400
            try:
                email = member.getProperty('email',getattr(member,'email',''))
            except AttributeError:
                email = getattr(member,'email','')
        else:
            email = ''
        return email.lower() or None

    def emailAddressesFrom(self,subscribers):
        """
        Convert a list of subscribers to a list of email addresses.

        Any of these which are usernames for which we can't find an
        address are converted to an obvious bogus address to help
        troubleshooting.
        """
        emails = []
        for s in subscribers:
            e = self.emailAddressFrom(s)
            # for troubleshooting, but breaks some MTAs
            #emails.append(e or 'NO_ADDRESS_FOR_%s' % s)
            if e: emails.append(e)
        return emails

    def usernamesFrom(self,subscriber):
        """
        Convert subscriber to username(s) if needed and return as a list.

        Ie if subscriber is a username, return that username; if
        subscriber is an email address, return the usernames of any CMF
        members with that email address.
        XXX too expensive, disabled; on plone.org with 7k members, this
        maxed out cpu for 10 minutes. Refactor.
        """
        if isUsername(subscriber):
            return [subscriber]
        else:
            return []
            # XXX plone.org performance issue
            #email = string.lower(subscriber)
            #usernames = []
            #folder = self.folder()
            #try:
            #    for user in folder.portal_membership.listMembers():
            #        member = folder.portal_memberdata.wrapUser(user)
            #        if string.lower(member.email) == email:
            #            usernames.append(member.name)
            #except AttributeError:
            #    pass
            #return usernames
        
InitializeClass(PageSubscriptionSupport)

class PageMailSupport:
    """
    This mixin class provides mail-out support and general mail utilities.
    """

    def isMailoutEnabled(self):
        """
        Has mailout been configured ?
        """
        if (self.mailhost() and
            (self.fromProperty() or self.replyToProperty())):
            return 1
        else:
            return 0

    def mailoutPolicy(self):
        """
        Get my mail-out policy - comments or edits ?
        """
        return getattr(self,'mailout_policy','comments')

    def fromProperty(self):
        """
        Give the mail_from property for this page.

        Usually acquires from the folder.
        """
        return getattr(self,'mail_from','')
    
    def replyToProperty(self):
        """
        Give the mail_replyto property for this page.

        Usually acquires from the folder.
        """
        return getattr(self,'mail_replyto','')
    
    def toProperty(self):
        """
        Give the mail_to property for this page.

        Usually acquires from the folder.
        """
        return getattr(self,'mail_to','')
    
    def fromHeader(self,REQUEST=None):
        """
        Give the appropriate From: header for mail-outs from this page.

        Tries to give the best attribution based on configuration and
        available information.  XXX todo: use an authenticated CMF
        member's email property
        """
        address = (self.fromProperty() or
                   #self.usersEmailAddress() or
                   self.replyToProperty())
        # splitlines to fend off header injection attacks from spammers
        lines = self.usernameFrom(REQUEST,ip_address=0).splitlines()
        realname = lines and lines[0] or _('anonymous')
        return '%s (%s)' % (address, realname)

    def replyToHeader(self):
        """
        Give the appropriate Reply-to: header for mail-outs from this page.
        """
        return self.replyToProperty() or self.fromProperty()
    
    def listId(self):
        """
        Give the "list id" for mail-outs from this page.
        """
        return self.fromProperty() or self.replyToProperty()
    
    def listPostHeader(self):
        """
        Give the appropriate List-Post: header for mail-outs from this page.
        """
        return '<mailto:%s>' % (self.listId())

    def listIdHeader(self):
        """
        Give the appropriate List-ID: header for mail-outs from this page.
        """
        return '%s <%s>' % (self.folder().title,self.listId())

    def xBeenThereHeader(self):
        """
        Give the appropriate X-Been-There: header for mail-outs from this page.
        """
        return self.listId()

    def bccHeader(self,recipients):
        """
        Give the appropriate Bcc: header for mail-outs from this page.

        Expects a list of recipient addresses.
        """
        return ', '.join(stripList(recipients))

    def subjectHeader(self,subject='',subjectSuffix=''):
        """
        Give the appropriate Subject: header for mail-outs from this page.

        - adds a prefix if configured in mail_subject_prefix;
        - includes page name in brackets unless disabled with mail_page_name
        - abbreviates issue tracker page names to just the number, except
          when creating the page or when overridden with mail_issue_name.
          Temp kludge: we assume the page is being created if it's less than
          30s old.
          (XXX tracker plugin dependency)
        - appends subjectSuffix if provided
        """
        if getattr(self.folder(),'mail_page_name',1):
            # we will add the page name
            if (self.issueNumber()
                and (self.getPhysicalRoot().ZopeTime()-self.creationTime()) > 30.0/24/60/60
                and not getattr(self.folder(),'mail_issue_name',0)):
                # we will truncate it to just the issue number
                pagename = '[#%s] ' % self.issueNumber()
            else:
                pagename = '[%s] ' % self.pageName()
        else:
            # page name has been suppressed
            pagename = ''
        return (
            getattr(self.folder(),'mail_subject_prefix','').strip() +
            pagename +
            subject +
            subjectSuffix.strip())

    def toHeader(self):
        """
        Give the appropriate To: header for mail-outs from this page.

        When sending a mail-out, we put the subscribers in Bcc for privacy.
        Something is needed in To, what should we use ?
        1. if there is a mail_to property, use that
        2. if there is a mail_replyto or mail_from property, use that.
           NB if you use a real address and also subscribe with it you may
           get duplicates; also when using the wiki mailin address a copy
           is sent quickly back to the wiki, possible cause of conflicts
           leading to slow comments ? Not recently.
        3. or use ";" which is a legal "nowhere" address but causes messy cc
           header in replies
        """
        return (self.toProperty() or
                self.replyToProperty() or
                self.fromProperty() or
                ';')

    def signature(self, message_id=None):
        """
        Give the appropriate signature to add to mail-outs from this page.

        That is:
        - the contents of the mail_signature property
        - or a semi-permalink to a comment if its message id is provided
        - or a link to this page
        """
        url = self.pageUrl()
        if message_id:
            # sync with makeCommentHeading
            url += '#msg%s' % re.sub(r'^<(.*)>$',r'\1',message_id) 
        return getattr(self.folder(),'mail_signature',
                       '--\nforwarded from %s' % url) # XXX i18n

    def mailhost(self):
        """
        Give the MailHost that should be used for sending mail, or None.

        This needs to just work, as follows: we want to find a real
        mailhost in a robust way, ie not relying only on a MailHost id,
        and acquiring it from a parent folder if necessary.  NB there are
        at least two kinds, a MaildropHost can be transaction-safe and
        prevents duplicates, a MailHost sends immediately and almost never
        sends duplicates in practice; we won't favour one or the other.
        So: look for the first object with Maildrop Host or Mail Host
        meta_type in this folder, then in the parent folder, and so on.
        """
        mhost = None
        folder = self.folder()
        # XXX folder might not have objectValues, don't know why (#938)
        while (not mhost) and folder and safe_hasattr(folder,'objectValues'):
            mhosts = folder.objectValues(
                spec=['Mail Host', 'Secure Mail Host', 'Maildrop Host', 'Secure Maildrop Host'])
            if mhosts: mhost = mhosts[0]
            folder = getattr(folder,'aq_parent',None)
        return mhost

    def sendMailToSubscribers(self, text, REQUEST, subjectSuffix='',
                              subject='',message_id=None,in_reply_to=None,
                              exclude_address=None):
        """
        Send mail to this page's and the wiki's subscribers, if any.
        
        If a mailhost and mail_from property have been configured and
        there are subscribers to this page, email text to them.  So as not
        to prevent page edits, catch any mail-sending errors (and log them
        and try to mail them to an admin).

        This is used for sending things of interest to all subscribers,
        like comments and page creations. To reduce noise we apply a few
        special cases:
        - if text is empty, don't send
        - if this is a boring page, don't send to wiki subscribers unless
          they've requested all edits
        """
        if text:
            self.sendMailTo(
                self.emailAddressesFrom(
                    self.subscriberList() + \
                    self.wikiSubscriberList(edits=self.isBoring())),
                text,
                REQUEST,
                subjectSuffix=subjectSuffix,
                subject=subject,
                message_id=message_id,
                in_reply_to=in_reply_to,
                exclude_address=exclude_address)

    def sendMailToEditSubscribers(self, text, REQUEST, subjectSuffix='',
                                  subject='',message_id=None,in_reply_to=None,
                                  exclude_address=None):
        """
        Send mail to this page's and the wiki's all edits subscribers, if any.
        
        Like sendMailToSubscribers, but sends only to the subscribers who
        have requested notification of all edits. If text is empty, send
        nothing.

        For backwards compatibility, a mailout_policy property with value
        edits on the wiki folder will override this and send to all
        subscribers.  I think that needs to go away as it makes the user's
        choice on subscribeform useless. During upgrade we could remove it
        and convert all subscribers to edits subscribers.
        """
        if not text: return
        if self.mailoutPolicy() == 'edits':        #XXX deprecate
            recipients = self.subscriberList() + \
                         self.wikiSubscriberList()
        else:
            recipients = self.subscriberList(edits=1) + \
                         self.wikiSubscriberList(edits=1)
        self.sendMailTo(
            self.emailAddressesFrom(recipients),
            text,
            REQUEST,
            subjectSuffix=subjectSuffix,
            subject=subject,
            message_id=message_id,
            in_reply_to=in_reply_to,
            exclude_address=exclude_address)
        
    def sendMailTo(self, recipients, text, REQUEST,
                   subjectSuffix='',
                   subject='',
                   message_id=None,
                   in_reply_to=None,
                   to=None,
                   exclude_address=None,
                   ):
        """Send a mail-out containing text to a list of email addresses.
        If mail-out is not configured in this wiki or there are no valid
        recipients, do nothing. Log any errors but don't stop.
        text can be body text or rfc-822 message text.
        """
        if not self.isMailoutEnabled(): return
        if exclude_address in recipients: recipients.remove(exclude_address) # help mailin.py avoid loops
        if not recipients: return
        try:
            msgid = message_id or self.messageIdFromTime(self.ZopeTime())
            fields = {
                'body':'%s\n\n%s' % (self.toencoded(text),self.toencoded(self.signature(msgid))),
                'From':self.toencoded(self.fromHeader(REQUEST)),
                'Reply-To':self.toencoded(self.replyToHeader()),
                'To':self.toencoded(to or self.toHeader()),
                'Bcc':self.toencoded(self.bccHeader(recipients)),
                'Subject':self.toencoded(self.subjectHeader(subject,subjectSuffix)),
                'Message-ID':self.toencoded(msgid),
                'In-Reply-To':self.toencoded((in_reply_to and '\nIn-reply-to: %s' % in_reply_to.splitlines()[0]) or ''),
                'Content-Type':'text/plain; charset="%s"' % self.encoding(),
                'charset':self.encoding(),
                'X-Zwiki-Version':self.zwiki_version(),
                'X-BeenThere':self.toencoded(self.xBeenThereHeader()),
                'List-Id':self.toencoded(self.listIdHeader()),
                'List-Post':self.toencoded(self.listPostHeader()),
                'List-Subscribe':'<'+self.pageUrl()+'/subscribeform>',
                'List-Unsubscribe': '<'+self.pageUrl()+'/subscribeform>',
                'List-Archive':'<'+self.pageUrl()+'>',
                'List-Help':'<'+self.wikiUrl()+'>',
                }
            AbstractMailHost(self.mailhost()).send(fields)
            BLATHER('sent mail to subscribers:\nTo: %s\nBcc: %s' % (fields['To'],fields['Bcc']))
        except: 
            BLATHER('**** failed to send mail to %s: %s' % (recipients,formattedTraceback()))
            
InitializeClass(PageMailSupport)

class AbstractMailHost:
    """Adapts the available [Secure] Mail[drop] Host to a generic one."""
    def __init__(self, mailhost):
        self.context = mailhost
    def send(self,fields):
        if self.context.meta_type in ('Secure Mail Host', 'Secure Maildrop Host'):
            r = self.context.secureSend(
                fields['body'],
                mto=fields['To'],
                mfrom=fields['From'],
                subject=fields['Subject'],
                mbcc=fields['Bcc'],
                charset=fields['charset'],
                **fields)
        else:
            msg = """\
From: %(From)s
Reply-To: %(Reply-To)s
To: %(To)s
Bcc: %(Bcc)s
Subject: %(Subject)s%(In-Reply-To)s
Message-ID: %(Message-ID)s
X-Zwiki-Version: %(X-Zwiki-Version)s
X-BeenThere: %(X-BeenThere)s
List-Id: %(List-Id)s
List-Post: %(List-Post)s
List-Subscribe: %(List-Subscribe)s
List-Unsubscribe: %(List-Unsubscribe)s
List-Archive: %(List-Archive)s
List-Help: %(List-Help)s
Content-Type: text/plain; charset="%(charset)s"

%(body)s
""" % fields
            r = self.context.send(msg)
        if r: BLATHER(r)

##############################################################################
# merged from..
"""
Zwiki's mailin external method - posts an incoming email message to a wiki

This external method receives a message in RFC2822 format and takes
appropriate action in the wiki where it has been called (eg, adding a
comment to one of the pages). This is usually invoked by a mail alias like::

 thewiki: |curl -n -F 'msg=<-' http://mysite/mywikifolder/mailin

See http://zwiki.org/HowToSetUpMailin for more help. For the delivery
algorithm, see the MailIn class docs below.

TODO:
friendly non-subscriber bounce messages
keep refactoring
size limit
html mail ?
file attachments ?
"""

import string
import email
from email.Message import Message
from email.Utils import parseaddr, getaddresses
from email.Iterators import typed_subpart_iterator

from Products.ZWiki.Regexps import bracketedexpr,urlchars
from Products.ZWiki.plugins.tracker.tracker import ISSUE_SEVERITIES

DEFAULT_SEVERITY = ISSUE_SEVERITIES[len(ISSUE_SEVERITIES)/2]

# use email aliases like these to influence delivery
WIKIADDREXP =    r'(wiki|mailin)@'         # comments and new pages
TRACKERADDREXP = r'(tracker|bugs|issues)@' # new tracker issues
SPAMADDREXP =    r'(spam)@'                # spam reports
MAILINADDREXP = r'(%s|%s|%s)' % (
    WIKIADDREXP,
    TRACKERADDREXP,
    SPAMADDREXP,
    )
PAGEINSUBJECTEXP = bracketedexpr
# extract a page name from the recipient real name
# because different things show up here - 'name', mail address, etc. -
# we recognize only page names beginning and ending with a word character
# and not containing @
#PAGEINREALNAMEEXP = r'(?=^[^@]*$).*?(?P<page>\w.*\w)' 
MAX_SIGNATURE_STRIP_SIZE = 500


class MailIn:
    """
    I represent an incoming mail message being posted to a wiki.

    I parse the incoming rfc2822 message string and expose the parts of
    interest, and (given a wiki context) figure out how to deliver myself.
    Here are the delivery rules:
    
    - if the message appears to be a zwiki mailout or from an auto-responder
      or junk, or it does't have a plain text part, DISCARD.
    
    - if we have been called in a page context (../SOMEPAGE/mailin), POST
      message as a comment on that page.
    
    - (DISABLED: select virtual host:
      Intended to allow a single mailin alias to serve many vhosts.  If there
      is a recipient of the form .*MAILINADDREXP@vhost where vhost matches a
      virtual host monster entry on this server, use that vhost's folder.
      )
    
    - if there is not at least one zwiki page in the current folder, DISCARD.
    
    - check sender's subscription status:
      unless the folder's mailin_policy property, possibly acquired, is
      'open', check that the sender is either subscribed somewhere in the wiki
      or listed in the mail_accept_nonmembers property, and if not BOUNCE the
      message.
    
    - if the recipient looks like a spam reporting address (.*SPAMADDREXP),
      UPDATE SPAM BLOCKING RULES and DISCARD (see updateSpamBlocks).
    
    - if the recipient looks like a tracker mailin address (.*TRACKERADDREXP),
      CREATE AN ISSUE page.  Otherwise,
    
    - identify destination page name: the first [bracketed page name] in the
      message subject, which may be a fuzzy/partial name; or the folder's
      default_mailin_page property, possibly acquired; or the first zwiki page
      in the folder - unless default_mailin_page was blank.
    
    - if no destination page could be found (default_mailin_page is
      blank/false), DISCARD.
    
    - if no wiki page by that name exists (fuzzy match allowed), CREATE it
    
    - POST message as a comment to that page
    
    """

    msg = None
    folder = None
    recipient = None
    destpage = None
    destpagename = None
    workingpage = None
    trackerissue = 0
    newpage = 0
    error = None

    def __init__(self,
                 context,
                 message,
                 ):
        """
        Extract the bits of interest from an RFC2822 message string.

        This perhaps should do the isJunk test up front to avoid
        unnecessary resource usage.
        """
        #BLATHER('mailin.py processing incoming message:\n%s' % message)
        BLATHER('mailin.py processing incoming message')
        self.context = context
        self.original = message
        self.msg = email.message_from_string(self.original)
        self.date = self.msg['Date']
        self.subject = re.sub(r'\n',r'',self.msg.get('Subject',''))
        self.realSubject = re.sub(r'.*?\[.*?\] ?(.*)',r'\1',self.subject)
        self.messageid = self.msg.get('Message-id','')
        self.inreplyto = self.msg.get('In-reply-to','')
        self.From = self.msg.get('From')
        self.FromRealName = parseaddr(self.From)[0]
        self.FromEmail    = parseaddr(self.From)[1]
        self.FromUserName = (self.FromRealName or
                             re.sub(r'@.*$',r'',self.FromEmail))
        self.sender = self.msg.get('Sender')
        self.senderEmail = (self.sender and
                            parseaddr(self.sender)[1]) or None
        tos = self.msg.get_all('to', [])
        ccs = self.msg.get_all('cc', [])
        resent_tos = self.msg.get_all('resent-to', [])
        resent_ccs = self.msg.get_all('resent-cc', [])
        self.recipients = getaddresses(tos + ccs + resent_tos + resent_ccs)

        # mailing list support
        # XXX x-beenthere is mailman-specific - need to support ezmlm & others here
        #self.xbeenthere = (self.msg.get('X-BeenThere') or
        #                   re.search(r'[^\s<]+@[^\s>]+',self.msg.get('Delivered-To')).group())
        # ..Type Error - configured ezmlm to provide beenthere instead (?)
        self.xbeenthere = self.msg.get('X-BeenThere')

        # the mailin body will be the message's first text/plain part
        try:
            firstplaintextpart = typed_subpart_iterator(self.msg,
                                                        'text',
                                                        'plain').next()
            payload = firstplaintextpart.get_payload(decode=1)
            content_encoding = self.msg.get_content_charset('ascii')
            payloadutf8 = payload.decode(content_encoding).encode('utf-8')
        except StopIteration:
            payloadutf8 = ''

        self.body = self.cleanupBody(payloadutf8)
        
    def isJunk(self):
        """
        Return true if this mail message should be silently ignored.

        Ideally, this should block mail loops, auto-responders and spam,
        but allow mailing list messages and mailouts from other zwikis.
        Currently it flags everything that looks like it came from a bot.
        Actually I don't think works as a way to filter autoresponders.
        We should make sure to include mailing headers in our mailouts
        and then most autoresponders should ignore us.

        qmail-autoresponder's bot-filtering procedure is reportedly good - see
        http://untroubled.org/qmail-autoresponder/procedure.txt .
        TMDA and spamassassin are two good spam filters - see
        http://software.libertine.org/tmda ,
        http://spamassassin.taint.org .
        """
        msgtext = self.original
        # a zwiki mailout
        if re.search(r'(?mi)^X-Zwiki-Version:',msgtext):
            return 1
        # the most common auto-response subject
        if re.search(r'(?mi)^Subject:.*out of office',msgtext):
            return 1
        # XXX don't need this ?
        # mailing list or low precedence mail
        # should allow these, but need to pass through the list loop
        # headers to avoid mail loop between mutually-subscribed zwiki and
        # mail list
        #if re.search(r'(?mi)^(List-ID|(X-)?Mailing-List|X-ML-Name):',msgtext):
        #    return 1
        #if re.search(
        #    r'(?mi)^List-(Help|Unsubscribe|Subscribe|Post|Owner|Archive):',msgtext):
        #    return 1
        #if re.search(r'(?mi)^Precedence:\s*(junk|bulk|list)\s*$',msgtext):
        #    return 1
        # no plaintext part
        if not self.body:
            return 1
        return 0

    def isSpamReport(self):
        """
        Return true if this message appears to be a spam report.
        """
        return re.search(SPAMADDREXP,self.recipientAddress()) and 1

    def updateSpamBlocks(self):
        """
        Update the wiki's spam-blocking rules based on this message.

        1. add any urls in the message body and/or attached message body to the
           folder's banned_links property, if it exists (can acquire)
        2. add the first ip address found in the message body, if any, to the
           folder's banned_ips property, if it exists (can acquire). 

        This means that any subscriber can forward a spam mailout to the
        wiki's spam address, and/or submit spammer urls or one spammer's
        IP address manually, and the banned_links/banned_ips properties
        will be updated. It's probably best to create these on the root
        folder; they will not be created automatically.

        XXX how to prevent frivolous reports ?

        XXX add support for banned_ips, see http://zwiki.org/BlockList.
        Better to use apache ? should we append to some filesystem config
        file instead ? make this a separate external method ?
        call add_spammer_url() and add_spammer_ip() for each ?
        
        """
        # update the banned links property
        if safe_hasattr(self.folder(),'banned_links'):
            banned_links = list(self.folder().banned_links)
            spam_links = re.findall(
                r'((?:http|https|ftp|mailto|file):/*%s)' % urlchars,
                self.subject + ' ' + self.body)
            added_links = []
            for l in spam_links:
                if l not in banned_links:
                    banned_links.append(l)
                    added_links.append(l)
            # have we got new urls to add ?
            if added_links:
                # update property - need to find the real  owner
                folder = self.folder()
                while not safe_hasattr(folder.aq_base,'banned_links'):
                    folder = folder.aq_parent
                folder.manage_changeProperties(banned_links=banned_links)
                # log, also try to notify admin by mail, for now
                log = 'mailin.py: added %s to %s/banned_links' % \
                      (added_links,string.join(folder.getPhysicalPath(),'/'))
                BLATHER(log)
                admin = getattr(self.folder(),'mail_admin',None)
                page = self.workingPage()
                if admin and page:
                    page.sendMailTo(
                        [],
                        log,
                        None,
                        subject='(banned_links updated)',
                        to=admin)

    def cleanupBody(self,body):
        """
        Clean up/remove uninteresting parts of an incoming message body.
        """
        # strip trailing newlines that seem to get added in transit
        body = re.sub(r'(?s)\n+$',r'\n',body)
        body = stripBottomQuoted(body)
        # strip Bob's signature
        body = self.stripSignature(body)
        return body

    def stripSignature(self,body):
        """
        Strip a signature after -- .

        Can't really do this safely; we'll strip only if it's below a
        certain size.
        """
        signature = re.search(r'(?s)\n--\n.*?$',body)
        signature = signature and signature.group()
        if signature and len(signature) <= MAX_SIGNATURE_STRIP_SIZE:
            body = re.sub(re.escape(signature),'',body)
        return body
    
    def contextIsPage(self):
        return self.context.meta_type=='ZWiki Page'
    
    def contextIsFolder(self):
        return not self.contextIsPage()
    
    def folder(self):
        """
        The wiki folder to which we are delivering.
        """
        if self.contextIsPage(): return self.context.aq_parent
        else: return self.context

    def recipient(self):
        """
        The recipient that was used to deliver here (an email tuple).

        This may be needed to determine the mailin action.  If the message
        has multiple recipients, decide which one refers to us as follows:
        - the first recipient matching the folder's mail_from property,
        - or the first one looking like a typical zwiki mailin alias (.*MAILINADDREXP),
        - or the first one.
        """
        if len(self.recipients) == 1:
            return self.recipients[0]
        folder_mail_from = getattr(self.folder(),'mail_from',None)
        if folder_mail_from:
            for r in self.recipients:
                if r[1] == folder_mail_from:
                    return r
        for r in self.recipients:
            if re.search(MAILINADDREXP,r[1]):
                return r
        return self.recipients[0]

    def recipientAddress(self):
        """
        Just the email address part of the recipient used to deliver here.
        """
        return self.recipient()[1]

    def workingPage(self):
        """
        Try to get a wiki page object which we can use for further operations.

        We'll try to ensure that new pages are parented somewhere sensible:
        the default mailin page if specified, or FrontPage, or the
        first page in the hierarchy.
        """
        allpages = self.folder().objectValues(spec='ZWiki Page')
        if allpages:
            alphafirst = allpages[0]
            outlinefirst = alphafirst.pageWithName(
                alphafirst.wikiOutline().first())
            frontpage = alphafirst.pageWithName('FrontPage')
            defaultmailinpage = alphafirst.pageWithName(
                getattr(self.folder(),'default_mailin_page',None))
            return defaultmailinpage or frontpage or outlinefirst or alphafirst
        else:
            return None
        
    def defaultMailinPage(self):
        """
        The name of the wiki's default destination page for mailins, or None.
        """
        return getattr(self.folder(),'default_mailin_page',
                       ((self.workingPage() and self.workingPage().pageName())
                        or None))
        
    def decideMailinAction(self):
        """
        Figure out what we should do with this mail-in.

        Fairly involved calculations trying to figure out what to do in a
        robust way (see the module docstring for more).  Sets
        self.destpage, self.destpagename, self.newpage, self.trackerissue,
        or sets a message in self.error if it can't.
        """
        if self.isJunk():
            self.error = '\nDiscarding junk mailin.\n\n\n'
            return

        if self.isSpamReport():
            BLATHER('mailin.py: processing spam report')
            self.updateSpamBlocks()
            self.error = '\nProcessed spam report.\n\n\n'
            return

        if self.contextIsPage():
            self.workingpage = self.context
        else:
            # an old mailin external method, in folder context
            self.workingpage = self.workingPage()
        if not self.workingpage:
            BLATHER('mailin.py: could not find a working page, discarding message')
            self.error = '\nCould not find a wiki page to work from, discarding message.\n\n\n'
            return

        self.checkMailinAllowed()
        if self.error: return

        # are we creating a tracker issue, which doesn't need a name ?
        # XXX todo: mail to tracker address is not always a new issue
        if re.search(TRACKERADDREXP,self.recipientAddress()):
            self.trackerissue = 1
            return

        # find the destination page name
        ## in the recipient's real name part if enabled..
        ##if self.checkrecipient:
        ##    m = re.search(PAGEINREALNAMEEXP,self.recipientRealName())
        ##    if m:
        ##        self.destpagename = m.group('page')
        # in the subject
        if (not self.destpagename):
            matches = re.findall(PAGEINSUBJECTEXP,self.subject)
            if matches:
                self.destpagename = matches[-1] # use rightmost
                # strip enclosing []'s
                self.destpagename = re.sub(bracketedexpr, r'\1',
                                           self.destpagename)
        # or use the default mailin page if any..
        if (not self.destpagename):
            self.destpagename = self.defaultMailinPage()

        # now, either we have the name of an existing page (fuzzy match
        # allowed)..
        page = (self.destpagename and
                self.workingpage.pageWithFuzzyName(self.destpagename,
                                                   allow_partial=1))
        if page:
            # also adjust working page to get right parentage etc.
            self.destpage = self.workingpage = page
            self.destpagename = self.destpage.pageName()
        # or we have the name of a new page to create..
        elif self.destpagename:
            self.newpage = 1
        # or we discard this message
        else:
            self.error = '\nMessage had no destination page, ignored.\n\n\n'
            BLATHER('mailin.py: message had no destination page, ignored')

    def checkMailinAllowed(self):
        """
        Check if the mailin determined by decideMailinAction() is permitted.

        Is the sender allowed to mail in here ?
        - if open posting is allowed, we'll accept anybody.
        - otherwise they must be a subscriber somewhere in the wiki
        - or be listed in the mail_accept_nonmembers property
          (useful to allow mailing lists, etc)
        Otherwise, set self.error.
        Requires self.workingpage to be already set up.
        """
        postingpolicy = getattr(self.folder(),'mailin_policy',None)
        accept = getattr(self.folder(),'mail_accept_nonmembers',[])
        if (postingpolicy == 'open' or
            self.FromEmail in accept or
            self.senderEmail in accept or
            # XXX poor caching
            self.workingpage.allSubscriptionsFor(self.FromEmail) or
            self.workingpage.allSubscriptionsFor(self.senderEmail)):
            return
        else:
            self.error = '\nSorry, you must be a subscriber to send mail to this wiki.\n\n\n'
            BLATHER('mailin.py: bounced mail from non-subscriber',
                    self.FromEmail)

#    def destinationVHost(self, msg):
#        """
#        Do tricky vhost-folder-finding.
#        
#        If we have one of the special recipients listed above along with a
#        matching virtual host, return the virtual host's folder; otherwise None.
#        Also save the username part of the matched recipient for later.
#        """
#        folder = None
#        vurt = getattr(self,'vurt',None)
#        if vurt and msg.wikiRecipients:
#            for address, realname in msg.wikiRecipients:
#                alias, host = address
#                # based on SiteAccess
#                # extract this -->
#                dict = getattr(vurt, 'domain_path', None)
#                if dict:
#                    real_host=None
#                    l_host = string.lower(host)
#                    if vurt.domain_path.has_key(l_host):
#                        real_host=l_host
#                    else:
#                        for hostname in vurt.domain_path.keys():
#                            if hostname[:2] == '*.':
#                                if string.find(l_host, hostname[2:]) != -1:
#                                    real_host = hostname
#                    # <--
#                    if real_host:
#                        path = vurt.domain_path[real_host]
#                        folder = self.getPhysicalRoot().unrestrictedTraverse(path)
#                        msg.aliasUsed = alias
#                        break
#        return folder

def stripBottomQuoted(body):
    origmsg = '(?:Original Message|message d\'origine)' # XXX i18n.. ?
    body = re.sub(r'(?smi)^-+%s-+$.*' % origmsg, '', body)
    return body


class PageMailinSupport:
    def mailin(self, msg):
        """
        See module docstring.
        """
        # parse and figure out how to deliver the message
        m = MailIn(self, msg)
        m.decideMailinAction()
        if m.error: return m.error

        # stash the sender's username in REQUEST as a hint for usernameFrom
        self.REQUEST.set('MAILIN_USERNAME', m.FromUserName)

        # now, create new page ?
        subject = m.realSubject
        subjectPrefix = ''
        if m.newpage:
            # XXX need to pass REQUEST for authentication ?  but "REQUEST has
            # no URL2" and create fails. Leave out for now.
            m.workingpage.create(m.destpagename,text='',sendmail=0)
            m.destpage = m.workingpage.pageWithName(m.destpagename)
            subjectPrefix = '(new) '

        # or new tracker issue ?
        elif m.trackerissue:
            # cf IssueNo0879
            # citations are normally formatted only within comments, but they
            # are often found in mailed-in issues and we'd like to display
            # these nicely. Options ?
            # - format them here as a special case. This means the mailout
            #   and page source contains ugly html.
            # - enable citation rendering everywhere. This deviates from
            #   standard STX etc.
            # - leave them unformatted
            # - post the issue details as a comment, not as the initial page
            #   text. Hey, that makes sense.        
            pagename = m.workingpage.createNextIssue(subject,
                                                     severity=DEFAULT_SEVERITY,
                                                     REQUEST=self.REQUEST,
                                                     sendmail=0)
            m.destpage = m.workingpage.pageWithName(pagename)
            subjectPrefix = '(new) '

        # add comment
        m.destpage.comment(text=m.body,
                           username=m.FromUserName,
                           REQUEST=self.REQUEST,
                           subject_heading=subjectPrefix+subject,
                           message_id=m.messageid,
                           in_reply_to=m.inreplyto,
                           sendmail=False
                           )

        # handle the mail-out ourselves, to pass through the original message
        m.destpage.sendMailToSubscribers(
            m.original,
            self.REQUEST, 
            subject=subjectPrefix+subject,
            message_id=m.messageid, 
            in_reply_to=m.inreplyto,
            # mailing list support: when a list and wiki are mutually subscribed,
            # and a mail comes in from the list, we want to forward it out to all
            # subscribers except the list, which has done it's own delivery.
            # Some lists will detect the duplicate automatically, for others we
            # expect the X-BeenThere header and tell zwiki to exclude that address.
            exclude_address=m.xbeenthere,
            )
        return None

InitializeClass(PageMailinSupport)

