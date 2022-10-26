# PageMailSupport mixin

import re, sys
from types import *
import string
import email
from email.Message import Message
from email.Utils import parseaddr, getaddresses
from email.Iterators import typed_subpart_iterator
from email.Header import Header, decode_header

from AccessControl.class_init import InitializeClass

from i18n import _
from TextFormatter import TextFormatter
from Utils import html_unquote,BLATHER,DEBUG,formattedTraceback,stripList, \
     isIpAddress,isEmailAddress,isUsername,safe_hasattr,tounicode,toencoded
from Defaults import AUTO_UPGRADE, PAGE_METATYPE
from Regexps import bracketedexpr,urlchars
from plugins.tracker.tracker import ISSUE_SEVERITIES

WIKIADDREXP      = r'(wiki|mailin)@'         # for comments and new pages
TRACKERADDREXP   = r'(tracker|bugs|issues)@' # for new tracker issues
MAILINADDREXP    = r'(%s|%s)' % (WIKIADDREXP,TRACKERADDREXP)
PAGEINSUBJECTEXP = bracketedexpr
DEFAULT_SEVERITY = ISSUE_SEVERITIES[len(ISSUE_SEVERITIES)/2]
MAX_SIGNATURE_STRIP_SIZE = 500
ORIGINAL_MESSAGE_HEADER = '(?:Original Message|message d\'origine)' # XXX i18n ?


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

    def _getSubscribers(self, parent=0): # -> [string]; depends on self, folder; modifies self, folder
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

    def _setSubscribers(self, subscriberlist, parent=0): # -> none; depends on self, folder; modifies self, folder
        """
        Set this page's subscriber list. 
        With parent flag, manage the parent folder's subscriber list instead.
        """
        if AUTO_UPGRADE: self._upgradeSubscribers()
        if parent:
            self.folder().subscriber_list = subscriberlist
        else:
            self.subscriber_list = subscriberlist

    def _resetSubscribers(self, parent=0): # -> none; modifies self, folder
        """
        Clear this page's subscriber list.
        With parent flag, manage the parent folder's subscriber list instead.
        """
        self._setSubscribers([],parent)

    def _upgradeSubscribers(self): # -> none; depends on self, folder; modifies self, folder
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
    def subscriberList(self, parent=0, edits=0): # -> [string]; depends on self, folder
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

    def isSubscriber(self, email, parent=0): # -> boolean; depends on self, folder
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
               
    def subscribe(self, email, REQUEST=None, parent=0, edits=0): # -> none; redirects; depends on self, folder; modifies self, folder, catalog
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

    def unsubscribe(self, email, REQUEST=None, parent=0): # -> none; redirects; depends on self, folder; modifies self, folder, catalog
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

    def wikiSubscriberList(self, edits=0): # -> [string]; depends on folder
        """whole-wiki version of subscriberList"""
        return self.subscriberList(parent=1,edits=edits)

    def isWikiSubscriber(self,email): # -> boolean; depends on folder
        """whole-wiki version of isSubscriber"""
        return self.isSubscriber(email,parent=1)

    def wikiSubscribe(self, email, REQUEST=None, edits=0): # -> none; redirects; depends on self, folder; modifies self, folder, catalog
        """whole-wiki version of subscribe"""
        return self.subscribe(email,REQUEST,parent=1,edits=edits)

    def wikiUnsubscribe(self, email, REQUEST=None): # -> none; redirects; depends on self, folder; modifies self, folder, catalog
        """whole-wiki version of unsubscribe"""
        return self.unsubscribe(email,REQUEST,parent=1)

    ## misc api methods ##################################################

    def pageSubscriberCount(self, edits=0): # -> integer; depends on self
        """The number of subscribers to this page.  With edits flag, count only
        subscribers who have requested all edits."""
        return len(self.subscriberList(parent=0,edits=edits))

    def wikiSubscriberCount(self, edits=0): # -> integer; depends on folder
        """The number of subscribers to the whole wiki.  With edits flag, count
        only subscribers who have requested all edits."""
        return len(self.subscriberList(parent=1,edits=edits))

    def subscriberCount(self, edits=0): # -> integer; depends on self, folder
        """The total number of subscribers to this page, including wiki
        subscribers.  With edits flag, count only subscribers who have
        requested all edits."""
        return self.pageSubscriberCount(edits) + self.wikiSubscriberCount(edits)

    def subscribeThisUser(self,REQUEST): # -> nothing; depends on self, folder, cmf/plone site, request; modifies self
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

    def allSubscriptionsFor(self, email): # -> [string]; depends on self, wiki, catalog
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
        # XXX obsolete, always have a catalog now ?
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

    def otherPageSubscriptionsFor(self, email): # -> [string]; depends on self, wiki
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

    def autoSubscriptionEnabled(self): # -> boolean; depends on self, folder
        return getattr(self,'auto_subscribe',0) and 1

    def usernameOrEmailOfSubscriber(self): # -> string; depends on cmf/plone site, request
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

    def emailAddressFrom(self,subscriber): # -> string; depends on cmf/plone site
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

    def emailAddressesFrom(self,subscribers): # -> [string]
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

    def usernamesFrom(self,subscriber): # -> [string]
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

    def isMailoutEnabled(self): # -> string; depends on self, folder, mailhost
        """
        Has mailout been configured ?
        """
        if (self.mailhost() and
            (self.fromProperty() or self.replyToProperty())):
            return 1
        else:
            return 0

    def mailoutPolicy(self): # -> string; depends on self, folder
        """
        Get my mail-out policy - comments or edits ?
        """
        return getattr(self,'mailout_policy','comments')

    def fromProperty(self): # -> string; depends on self, folder
        """
        Give the mail_from property for this page.

        Usually acquires from the folder.
        """
        return getattr(self,'mail_from','')
    
    def replyToProperty(self): # -> string; depends on self, folder
        """
        Give the mail_replyto property for this page.

        Usually acquires from the folder.
        """
        return getattr(self,'mail_replyto','')
    
    def toProperty(self): # -> string; depends on self, folder
        """
        Give the mail_to property for this page.

        Usually acquires from the folder.
        """
        return getattr(self,'mail_to','')
    
    def fromHeader(self,REQUEST=None): # -> string; depends on self, folder
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

    def replyToHeader(self): # -> string; depends on self, folder
        """
        Give the appropriate Reply-to: header for mail-outs from this page.
        """
        return self.replyToProperty() or self.fromProperty()
    
    def listId(self): # -> string; depends on self, folder
        """
        Give the "list id" for mail-outs from this page.
        """
        return self.fromProperty() or self.replyToProperty()
    
    def listPostHeader(self): # -> string; depends on self, folder
        """
        Give the appropriate List-Post: header for mail-outs from this page.
        """
        return '<mailto:%s>' % (self.listId())

    def listIdHeader(self): # -> string; depends on self, folder
        """
        Give the appropriate List-ID: header for mail-outs from this page.
        """
        return '%s <%s>' % (self.folder().title,self.listId())

    def xBeenThereHeader(self): # -> string; depends on self, folder
        """
        Give the appropriate X-Been-There: header for mail-outs from this page.
        """
        return self.listId()

    def bccHeader(self,recipients): # -> string
        """
        Give the appropriate Bcc: header for mail-outs from this page.

        Expects a list of recipient addresses.
        """
        return ', '.join(stripList(recipients))

    def subjectHeader(self,subject='',subjectSuffix=''): # -> string; depends on self, folder, time
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
            self.tounicode(getattr(self.folder(),'mail_subject_prefix','').strip()) +
            self.tounicode(pagename) +
            self.tounicode(subject) +
            self.tounicode(subjectSuffix.strip()))

    def toHeader(self): # -> string; depends on self, folder
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

    def signature(self, message_id=None): # -> string; depends on self, folder
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

    def mailhost(self): # -> mailhost; depends on: folder context
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
        When multiple mailhosts are found in one folder, choose the
        alphabetically first.
        """
        mhost = None
        folder = self.folder()
        # XXX folder might not have objectValues, don't know why (#938)
        while (not mhost) and folder and safe_hasattr(folder,'objectValues'):
            mhostids = sorted(folder.objectIds(
                spec=['Mail Host', 'Secure Mail Host', 'Maildrop Host', 'Secure Maildrop Host']))
            if mhostids: mhost = folder[mhostids[0]]
            folder = getattr(folder,'aq_parent',None)
        return mhost

    def sendMailToSubscribers(self, text, REQUEST, subjectSuffix='',
                              subject='',message_id=None,in_reply_to=None,
                              exclude_address=None): # -> none; depends on self, wiki, mailhost; other effects: sends mail
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
                                  exclude_address=None): # -> none; depends on self, wiki, mailhost; other effects: sends mail
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
                   ): # -> none; depends on self, wiki, mailhost, time; other effects: sends encoded msg
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
            # encode subject with RFC 2047
            subj = str(Header(self.subjectHeader(subject,subjectSuffix), self.encoding()))
            fields = {
                'body':'%s\n\n%s' % (self.toencoded(text),self.toencoded(self.signature(msgid))),
                'From':self.toencoded(self.fromHeader(REQUEST)),
                'Reply-To':self.toencoded(self.replyToHeader()),
                'To':self.toencoded(to or self.toHeader()),
                'Bcc':self.toencoded(self.bccHeader(recipients)),
                'Subject':subj,
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
            GenericMailHost(self.mailhost()).send(fields)
            BLATHER('sent mail to subscribers:\nTo: %s\nBcc: %s' % (fields['To'],fields['Bcc']))
        except: 
            BLATHER('**** failed to send mail to %s: %s' % (recipients,formattedTraceback()))
            
InitializeClass(PageMailSupport)

class GenericMailHost:
    """Adapts the available [Secure] Mail[drop] Host to a generic one."""
    def __init__(self, mailhost): # -> none
        self.context = mailhost
    def send(self,fields): # -> none; depends on: self, mailhost; other effects: sends msg
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


class PageMailinSupport:
    def mailin(self, msg): # -> string | none; depends on self, wiki; modifies wiki
        """Handle an incoming email message, eg by posting a comment or
        creating a page. See the MailIn helper class for the precise
        delivery rules.  msg is a string containing a RFC2822 message.
        This is usually invoked by a mail server alias like::

           wiki:|curl -n -F 'msg=<-' http://site/wikifolder/ANYPAGE/mailin

        See http://zwiki.org/HowToSetUpMailin for more help.

        XXX todo:
        pass through original mail with attachments
        non-subscriber bounce messages ?
        """
        m = MailIn(self, msg)
        action, info = m.decideMailinAction()
        if not action in ('COMMENT','CREATE','ISSUE'): return info
        self.REQUEST.set('MAILIN_USERNAME', m.FromUserName) # a hint for usernameFrom
        subject = m.realSubject
        if action == 'CREATE':
            subjectprefix = '(new) '
            pagename = self.create(info,text='',sendmail=0)
        elif action == 'ISSUE':
            subjectprefix = '(new) '
            pagename = self.createNextIssue(subject,severity=DEFAULT_SEVERITY,REQUEST=self.REQUEST,sendmail=0)
        else:
            subjectprefix = ''
            pagename = info
        self.pageWithName(pagename).comment(text=m.body,
                                            username=m.FromUserName,
                                            REQUEST=self.REQUEST,
                                            subject_heading=subjectprefix+subject,
                                            message_id=m.messageid,
                                            in_reply_to=m.inreplyto,
                                            )

#         # handle the mail-out ourselves, to pass through the original message
#         m.destpage.sendMailToSubscribers(
#             m.original,
#             self.REQUEST, 
#             subject=subjectPrefix+subject,
#             message_id=m.messageid, 
#             in_reply_to=m.inreplyto,
#             # mailing list support: when a list and wiki are mutually subscribed,
#             # and a mail comes in from the list, we want to forward it out to all
#             # subscribers except the list, which has done it's own delivery.
#             # Some lists will detect the duplicate automatically, for others we
#             # expect the X-BeenThere header and tell zwiki to exclude that address.
#             exclude_address=m.xbeenthere,
#             )
#         return None

    def defaultMailinPageName(self): # -> string | none; depends on self, folder
        """The name of the wiki's default destination page for mailins, or
        None.  This is specified by the default_mailin_page property, or
        is None if that property is blank, otherwise is the current page.
        """
        if safe_hasattr(self.folder(),'default_mailin_page'):
            return self.folder().default_mailin_page or None
        else:
            return self.pageName()
        
InitializeClass(PageMailinSupport)

class MailIn:
    """
    I represent an incoming mail message being posted to a wiki.  I parse
    the rfc2822 message string and figure out how to deliver myself within
    the provided wiki context.
    """
    def __init__(self, context, message): # -> none
        """Extract the bits of interest from an RFC2822 message string.
        context should be a wiki page. This perhaps should do the isJunk
        test up front to avoid unnecessary resource usage.
        """
        DEBUG('mailin.py processing incoming message:\n%s' % message)
        self.context      = context
        self.original     = message
        self.msg          = email.message_from_string(self.original)
        self.date         = self.msg['Date']
        # flatten a multi-line subject into one line
        s = re.sub('\n','',self.msg.get('Subject',''))
        # convert the possibly RFC2047-encoded subject to unicode.
        # Only the first encoded part is used if there is more than one.
        # misencoded subjects are ignored.
        (s,enc)           = decode_header(s)[0]
        try:
            self.subject  = tounicode(s,enc or 'ascii')
        except UnicodeDecodeError:
            self.subject  = ''
        self.realSubject  = re.sub(r'.*?\[.*?\] ?(.*)',r'\1',self.subject)
        self.messageid    = self.msg.get('Message-id','')
        self.inreplyto    = self.msg.get('In-reply-to','')
        self.From         = self.msg.get('From')
        self.FromRealName = parseaddr(self.From)[0]
        self.FromEmail    = parseaddr(self.From)[1]
        self.FromUserName = (self.FromRealName or re.sub(r'@.*$',r'',self.FromEmail))
        self.sender       = self.msg.get('Sender')
        self.senderEmail  = (self.sender and parseaddr(self.sender)[1]) or None
        tos               = self.msg.get_all('to', [])
        ccs               = self.msg.get_all('cc', [])
        resent_tos        = self.msg.get_all('resent-to', [])
        resent_ccs        = self.msg.get_all('resent-cc', [])
        self.recipients   = getaddresses(tos + ccs + resent_tos + resent_ccs)
        # mailing list support
        # XXX x-beenthere is mailman-specific - need to support ezmlm & others here
        #self.xbeenthere = (self.msg.get('X-BeenThere') or
        #                   re.search(r'[^\s<]+@[^\s>]+',self.msg.get('Delivered-To')).group())
        # ..Type Error - configured ezmlm to provide beenthere instead (?)
        self.xbeenthere = self.msg.get('X-BeenThere')
        # the mailin body will be the message's first text/plain part
        # (or a null string if there is none or it's misencoded)
        try:
            firstplaintextpart = typed_subpart_iterator(self.msg,
                                                        'text',
                                                        'plain').next()
            # as I understand it:
            # first decoding, from the content-transfer-encoding, eg quoted-printabe
            payload = firstplaintextpart.get_payload(decode=1)
            # second decoding, from utf8 or whatever to unicode
            charset = self.msg.get_content_charset('ascii')
            payloadutf8 = payload.decode(charset).encode('utf-8')
        except (StopIteration, UnicodeDecodeError):
            payloadutf8 = ''
        self.body = cleanupBody(payloadutf8)
        
    def decideMailinAction(self): # -> (string, string|none); depends on: self, wiki context
        """
        Figure out what to do with this mail-in. Returns an (action, info)
        pair where action is one of 'ERROR', 'ISSUE', 'CREATE', 'COMMENT'
        and info is an error message, None, or page name.  Here are the
        delivery rules:

        - if the message appears to be a zwiki mailout or from an auto-responder
          or junk, or it doesn't have a plain text part, DISCARD.

        - check that the sender is either subscribed somewhere in the wiki
          or listed in the mail_accept_nonmembers property, or the
          folder's mailin_policy property (possibly acquired) is 'open';
          otherwise BOUNCE.

        - if the recipient looks like a tracker mailin address (.*TRACKERADDREXP),
          CREATE AN ISSUE PAGE.

        - identify the destination page name: the last [bracketed page name] 
          in the message subject, or the folder's default_mailin_page
          property (possibly acquired) or the current page (unless
          default_mailin_page was blank in which case DISCARD.)

        - if the destination page does not exist (partial fuzzy matches
          allowed), CREATE it..

        - and post the message there as a COMMENT.
        """
        if self.isJunk(): return ('ERROR','\nDiscarding junk mailin.\n\n\n')
        if not self.isMailinAllowed():
            DEBUG('ignoring mail from non-subscriber',self.FromEmail)
            return ('ERROR', '\nSorry, you must be a subscriber to send mail to this wiki.\n\n\n')
        if re.search(TRACKERADDREXP,self.recipientAddress()): return ('ISSUE',None)
        pagename = pageNameFromSubject(self.subject) or self.context.defaultMailinPageName()
        if not pagename: return ('ERROR','\nMessage has no destination page, ignored.\n\n\n')
        page = self.context.pageWithFuzzyName(pagename,allow_partial=1)
        if page: return ('COMMENT',page.pageName())
        else: return ('CREATE',pagename)

    def isMailinAllowed(self): # -> boolean; depends on self, folder
        """Check if this mailin is permitted to the sender. They must be
        subscribed somewhere in the wiki, or be in the
        mail_accept_nonmembers property, or the mailin_policy property
        must be 'open'.
        """
        def is_subscriber(e): return len(self.context.allSubscriptionsFor(e)) > 0 # XXX poor caching
        postingpolicy = getattr(self.context.folder(),'mailin_policy',None)
        allowlist = getattr(self.context.folder(),'mail_accept_nonmembers',[])
        return (postingpolicy == 'open'
                or self.FromEmail in allowlist
                or self.senderEmail in allowlist
                or is_subscriber(self.FromEmail)
                or is_subscriber(self.senderEmail))

    def isJunk(self): # -> boolean; depends on: self
        """Return true if this mail message should be silently ignored.
        Ideally, this should block mail loops, auto-responders and spam,
        but allow mailing list messages and mailouts from other zwikis.
        qmail-autoresponder's bot-filtering procedure is reportedly good - see
        http://untroubled.org/qmail-autoresponder/procedure.txt .
        TMDA and spamassassin are two good spam filters - see
        http://software.libertine.org/tmda ,
        http://spamassassin.taint.org .
        """
        return (
            re.search(r'(?mi)^X-Zwiki-Version:', self.original)
            or re.search(r'(?mi)^Subject:.*out of office', self.original)
            or not self.body
            ) and True or False

    def recipient(self): # -> email lib address tuple; depends on self, folder
        """
        Identify the recipient that was used to deliver here (as an email tuple).

        If the message has multiple recipients, decide which of them
        refers to us as follows:
        - the first recipient matching the folder's mail_from property,
        - or the first one looking like a typical zwiki mailin alias (.*MAILINADDREXP),
        - or the first one.
        """
        if len(self.recipients) == 1:
            return self.recipients[0]
        folder_mail_from = getattr(self.context.folder(),'mail_from',None)
        if folder_mail_from:
            for r in self.recipients:
                if r[1] == folder_mail_from:
                    return r
        for r in self.recipients:
            if re.search(MAILINADDREXP,r[1]):
                return r
        return self.recipients[0]

    def recipientAddress(self): # -> string; depends on self, folder
        """Just the email address part of the recipient used to deliver here."""
        return self.recipient()[1]

def cleanupBody(body): # -> string
    """Clean up/remove uninteresting parts of an incoming message body."""
    body = re.sub(r'(?s)\n+$',r'\n',body) # trailing newlines added in transit
    body = stripBottomQuoted(body)
    body = stripSignature(body)
    return body

def stripBottomQuoted(body): # -> string
    return re.sub(r'(?smi)^-+%s-+$.*' % ORIGINAL_MESSAGE_HEADER, '', body)

def stripSignature(body): # -> string
    """Strip a signature after -- . To reduce false positives, we'll strip
    only if it's below a certain size.
    """
    signature = re.search(r'(?s)\n--\n.*?$',body)
    signature = signature and signature.group()
    if signature and len(signature) <= MAX_SIGNATURE_STRIP_SIZE:
        body = re.sub(re.escape(signature),'',body)
    return body

def pageNameFromSubject(subject): # -> string | none
    matches = re.findall(PAGEINSUBJECTEXP,subject)
    if matches:
        pagename = matches[-1] # if more than one, use rightmost
        pagename = re.sub(bracketedexpr,r'\1',pagename)
        return pagename
    else:
        return None
