# MailSupport mixin

import string, re, sys
from string import split,join,find,lower,rfind,atoi,strip,lstrip
from types import *

from TextFormatter import TextFormatter
from Utils import html_unquote,BLATHER,formattedTraceback,stripList
from Defaults import AUTO_UPGRADE, PAGE_METATYPE

class MailSupport:                 
    """
    This mixin class provides subscription and wikimail support.

    Responsibilities: manage a list of subscribers for both this page and
    it's folder, and expose these in the ZMI; also provide wikimail
    utilities and auto-upgrade support.

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
            if hasattr(self.folder(),'subscriber_list'):
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
        if (hasattr(f, 'subscribers') and
            type(f.subscribers) is StringType):
            if f.subscribers:
                oldsubs = split(re.sub(r'[ \t]+',r'',f.subscribers),',')
            try:
                del f.subscribers
            except KeyError:
                BLATHER('failed to delete self.folder().subscribers')
            changed = 1
        elif hasattr(f, '_subscribers'):
            oldsubs = f._subscribers.keys()
            try:
                del f._subscribers
            except KeyError:
                BLATHER('failed to delete self.folder()._subscribers')
            changed = 1
        # ensure a subscriber_list attribute
        if not hasattr(f, 'subscriber_list'): f.subscriber_list = []
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
        if (hasattr(self, 'subscribers') and
            type(self.subscribers) is StringType):
            if self.subscribers:
                oldsubs = split(re.sub(r'[ \t]+',r'',self.subscribers),',')
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
        if hasattr(self, '_subscribers'):
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

    def subscriberList(self, parent=0):
        """
        Return a list of this page's subscribers
        With parent flag, manage the parent folder's subscriber list instead.
        """
        return self._getSubscribers(parent)

    def subscriberCount(self, parent=0):
        """
        Return the number of subscribers currently subscribed to this page
        With parent flag, count the parent folder's subscriber list
        instead.
        """
        return len(self.subscriberList(parent))

    def isSubscriber(self,email,parent=0):
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
            if email: email = string.lower(email)
            usernames = self.usernamesFrom(subscriber)
            for sub in self.subscriberList(parent):
                if not sub: continue
                if ((email and (string.lower(sub) == email)) or
                    (usernames and (sub in usernames))):
                    return 1
        return 0
               
    def subscribe(self, email, REQUEST=None, parent=0):
        """
        Add email as a subscriber to this page.  With parent flag, add to
        the parent folder's subscriber list instead.
        """
        subscriber = email
        if subscriber:
            if not self.isSubscriber(subscriber,parent):
                BLATHER('subscribed',subscriber,'to',self.id())
                subs = self._getSubscribers(parent)
                subs.append(subscriber)
                self._setSubscribers(subs,parent)
                if not parent: self.index_object()
        if REQUEST:
            REQUEST.RESPONSE.redirect(
                REQUEST.get('redirectURL',
                            REQUEST['URL1']+'/subscribeform?email='+subscriber))

    def unsubscribe(self, email, REQUEST=None, parent=0):
        """
        Remove email from this page's subscriber list.  With parent
        flag, remove from the parent folder's subscriber list instead.
        Does not attempt to look up the username from an email address
        or vice-versa, so you must unsubscribe the correct one.
        """
        subscriber = email
        if self.isSubscriber(subscriber,parent):
            sl = self.subscriberList(parent)
            for s in sl:
                if string.lower(s) == string.lower(subscriber):
                    BLATHER('unsubscribed',subscriber,'from',self.id())
                    sl.remove(s)
            self._setSubscribers(sl,parent)
            if not parent: self.index_object()
        if REQUEST:
            REQUEST.RESPONSE.redirect(
                REQUEST.get('redirectURL',
                            REQUEST['URL1']+'/subscribeform?email='+subscriber))

    ## folder subscription api ###########################################

    def wikiSubscriberList(self):
        """whole-wiki version of subscriberList"""
        return self.subscriberList(parent=1)

    def wikiSubscriberCount(self):
        """whole-wiki version of subscriberCount"""
        return self.subscriberCount(parent=1)

    def isWikiSubscriber(self,email):
        """whole-wiki version of isSubscriber"""
        return self.isSubscriber(email,parent=1)

    def wikiSubscribe(self, email, REQUEST=None):
        """whole-wiki version of subscribe"""
        return self.subscribe(email,REQUEST,parent=1)

    def wikiUnsubscribe(self, email, REQUEST=None):
        """whole-wiki version of unsubscribe"""
        return self.unsubscribe(email,REQUEST,parent=1)

    ## misc api methods ##################################################

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

    def allSubscribers(self):
        """
        Return a list of subscribers to this page or the whole wiki.

        Special case: if this page is named TestPage or SandBox, return
        only the page subscribers. (Only page subscribers will receive
        mail from these pages.)
        """
        subs = []
        subs.extend(self.subscriberList()) # copy, don't reference
        if self.title_or_id() not in ['TestPage','SandBox']: 
            for s in self.wikiSubscriberList():
                if not (s in subs): subs.append(s)
        return subs

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
        if email: email = string.lower(email)
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
                    if ((email and (string.lower(sub) == email)) or
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

    ## utilities ################################################

    def isMailoutEnabled(self):
        """
        True if mailout has been configured
        """
        if (hasattr(self,'MailHost') and
            (getattr(self.folder(),'mail_from',None) or
             getattr(self.folder(),'mail_replyto',None))):
            return 1
        else:
            return 0

    def mailoutPolicy(self):
        """
        Get my mail-out policy - comments or edits ?
        """
        return getattr(self,'mailout_policy','comments')

    def autoSubscriptionEnabled(self):
        if getattr(self,'auto_subscribe',0):
            return 1
        else:
            return 0

    def isEmailAddress(self,s):
        """
        True if s looks like an email address.
        """
        if s and '@' in s: return 1
        else: return 0
    
    def isUsername(self,s):
        """
        True if s looks like a username.
        """
        return not self.isEmailAddress(s)
    
    def emailAddressFrom(self,subscriber):
        """
        Convert subscriber to an email address, if needed.

        If subscriber is an email address, return as-is.  Otherwise assume
        it's a username and try to look up the corresponding CMF member's
        email address.  Otherwise return None.
        """
        if self.isEmailAddress(subscriber):
            return subscriber
        else:
            folder = self.folder()
            try:
                user = folder.portal_membership.getMemberById(subscriber)
                member = folder.portal_memberdata.wrapUser(user)
                return member.email
            except AttributeError:
                return None

    def emailAddressesFrom(self,subscribers):
        """
        Convert a list of subscribers to a list of email addresses.
        """
        emails = []
        for s in subscribers:
            e = self.emailAddressFrom(s)
            if e: emails.append(e)
        return emails

    def usernamesFrom(self,subscriber):
        """
        Convert subscriber to username(s) if needed and return as a list.

        Ie if subscriber is a username, return that username; if
        subscriber is an email address, return the usernames of any CMF
        members with that email address.

        XXX too expensive; on plone.org with 7k members, this maxed out
        cpu for 10 minutes.
        
        """
        if self.isUsername(subscriber):
            return [subscriber]
        else:
            return []
            # XXX
        
            email = string.lower(subscriber)
            usernames = []
            folder = self.folder()
            try:
                for user in folder.portal_membership.listMembers():
                    member = folder.portal_memberdata.wrapUser(user)
                    if string.lower(member.email) == email:
                        usernames.append(member.name)
            except AttributeError:
                pass
            return usernames

    def messageIdFromTime(self,time):
        """
        Generate a somewhat unique email message-id based on a DateTime
        """
        msgid = time.strftime('%Y%m%d%H%M%S')+time.rfc822()[-5:]+'@'
        if hasattr(self,'REQUEST'):
            msgid += re.sub(r'http://','',self.REQUEST.get('SERVER_URL',''))
        msgid = '<%s>' % msgid
        return msgid

    def sendMailToSubscribers(self, text, REQUEST, subjectSuffix='',
                              subject='',message_id=None,in_reply_to=None,
                              exclude_address=None):
        """
        Send mail to page subscribers.
        
        If a mailhost and mail_from property have been configured and
        there are subscribers to this page, email text to them.  So as not
        to prevent page edits, catch any mail-sending errors (and log and
        try to forward them to an admin).
        """

        recipients = self.emailAddressesFrom(self.allSubscribers())

	# mailin may tell us to exclude a mailing list address to prevent a loop
        try: recipients.remove(exclude_address)
        except ValueError: pass

	# some lists (ezmlm) require the list address in To, and if it also 
	# appears in subscriber_list will deliver two copies. Just remove
	# duplicates to be safe.
	def uniq(list):
            u = []
            for i in list:
                if not i in u: u.append(i)
	    return u
        recipients = uniq(recipients)

        if not recipients: return
	
        try:
            self.sendMailTo(recipients,text,REQUEST,
                            subjectSuffix=subjectSuffix,
                            subject=subject,
                            message_id=message_id,
                            in_reply_to=in_reply_to)
        except:
            BLATHER('failed to send mail to %s: %s' % (recipients,
                                                    formattedTraceback()))
            admin = getattr(self.folder(),'mail_admin',None)
            if admin:
                try: self.sendMailTo(
                    [admin],text or '(no text)',REQUEST,
                    subjectSuffix='ERROR, subscriber mailout failed')
                except:
                    BLATHER('failed to send error report to admin: %s' % \
                         formattedTraceback())

    # XXX refactor
    # todo: use an authenticated CMF member's email property when appropriate
    def sendMailTo(self, recipients, text, REQUEST, subjectSuffix='',
                   subject='',message_id=None,in_reply_to=None):
        """
        Send mail to the specified recipients.

        If a mailhost and mail_from property have been configured,
        attempt to email text to recipients.

        Does all kinds of careful stuff with properties
        and other info to provide the best possible headers.
        Refactor.
        """
        if not self.isMailoutEnabled(): return

        # XXX try unformatted mailouts again (IssueNo0696)
        #mailouttext = self.formatMailout(text)
        mailouttext = text

        # gather bits and pieces
        mhost=self.MailHost
        username = self.usernameFrom(REQUEST)
        if not message_id:
            message_id = self.messageIdFromTime(self.ZopeTime())
        mail_from = getattr(self.folder(),'mail_from','')
        mail_replyto = getattr(self.folder(),'mail_replyto','')
        replytohdr = mail_replyto or mail_from
        listid = mail_from or mail_replyto
        # primary recipient, alternatives:
        # 1. "To: ;" causes messy cc header in replies, while
        # 2. "To: replytohdr" sends a copy back to the wiki which
        # may be the cause of intermittent slow comments
        # XXX for now use 2 & allow it to be overridden 
        tohdr = getattr(self.folder(),'mail_to','') or replytohdr
        if mail_from:
            if (not re.match(r'[0-9\.\s]*$',username) and
                not self.isEmailAddress(username)):
                fromhdr = '%s (%s)' % (mail_from,username)
            else:
                fromhdr = mail_from
        else:
            if self.isEmailAddress(username):
                fromhdr = username
            elif re.match(r'[0-9\.\s]*$',username):
                fromhdr = mail_replyto
            else:
                fromhdr = '%s (%s)' % (mail_replyto,username)
        # link to message - copied from makeCommentHeading
        pageurl = self.page_url()
        pageurl += '#msg'+re.sub(r'^<(.*)>$',r'\1',message_id) 
        if getattr(self.folder(),'mail_page_name',1):
            pagename = '[%s] ' % self.title_or_id()
        else:
            pagename = ''
        signature = getattr(self.folder(),
                            'mail_signature',
                            '--\nforwarded from %s' % pageurl)
                           
        # send message - XXX templatize this
        # XXX - ezmlm won't deliver bulk, but that's what these are, what to do
        #Precedence: bulk
	# XXX - also, it's not catching duplicate message ids/message contents
	# or not delivering to sender like mailman can.. oh what to do
        #Delivered-To: %s
        msg = """\
From: %s
Reply-To: %s
To: %s
Bcc: %s
Subject: %s
Message-ID: %s%s
X-BeenThere: %s
X-Zwiki-Version: %s
List-Id: %s <%s>
List-Post: <mailto:%s>
List-Subscribe: <%s/subscribeform>
List-Unsubscribe: <%s/subscribeform>
List-Archive: <%s>
List-Help: <%s>

%s
%s
""" \
        % (fromhdr,
           replytohdr,
           tohdr,
           join(stripList(recipients), ', '),
           join([strip(getattr(self.folder(),'mail_subject_prefix',
                               '')), #getattr(self.folder(),'title'))),
                 #strip(self.id()),
                 pagename,
                 subject,
                 strip(subjectSuffix)],''),
           message_id,
           (in_reply_to and '\nIn-reply-to: %s' % in_reply_to) or '',
           listid,
           self.zwiki_version(),
           self.folder().title, listid,
           listid,
           pageurl,
           pageurl,
           pageurl,
           self.wiki_url(),
           mailouttext,
           signature,
           )

        # testing support: messages with subject [test] or originating
        # from TestPage are not mailed out to subscribers
        if (subject == '[test]' or self.title_or_id() == 'TestPage'):
            # log and drop it
            BLATHER('discarding test mailout:\n%s' % msg)
            # I tried redirecting to a test SMTP server but it blocked
            #BLATHER('diverting test mailout to test server:\n%s' % msg)
            #try:
            #    self.TestMailHost.send(msg)
            #    BLATHER('sent mailout to test server')
            #    BLATHER('TestMailHost info:',
            #         self.TestMailHost.smtp_host,
            #         self.TestMailHost.smtp_port)
            #except:
            #    type, val, tb = sys.exc_info()
            #    err = string.join(
            #        traceback.format_exception(type,val,tb),'')
            #    BLATHER('failed to send mailout to test server:',
            #         err,
            #         self.TestMailHost.smtp_host,
            #         self.TestMailHost.smtp_port)
            # instead, I sent as usual and hacked mailman to drop it
            # do add a X-No-Archive header
            #msg = re.sub(r'(?m)(List-Help:.*$)',
            #             r'\1\nX-No-Archive: yes',
            #             msg)
            #BLATHER('sending mailout:\n%s' % msg)
            #mhost.send(msg)
        else:
            BLATHER('sending mailout:\n%s' % msg)
            mhost.send(msg)
        # cc comments to an IRC channel via ciabot (or similar)
        # sent separately so we can provide the special subject 
        mail_irc_address = getattr(self.folder(),'mail_irc_address',None)
        mail_irc_subject = getattr(self.folder(),'mail_irc_subject','')
        if mail_irc_address:
            mhost.send("""\
From: %s
To: %s
Subject: %s

%s: %s
%s
""" \
            % (fromhdr,
               mail_irc_address,
               mail_irc_subject,
               username,
               mailouttext,
               signature,
               ))
            BLATHER("""sending mailout to IRC:
From: %s
To: %s
Subject: %s

%s: %s
%s
""" \
            % (fromhdr,
               mail_irc_address,
               mail_irc_subject,
               username,
               mailouttext,
               signature,
               ))

    def formatMailout(self, text):
        """
        Format some text (usually a page diff) for email delivery.

        This is supposed to present a diff, but in the most human-readable
        and clutter-free way possible, since people may be receiving many
        of these. In the case of a simple comment, it should look as if
        the comment was just forwarded out.  See
        test_formatMailout/testEndToEndCommentFormatting for examples.

        """
        if not text: return ''
        
        # try to do some useful formatting
        # wrap and fill each paragraph, except indented ones,
        # and preserve citation prefixes
        paragraphs = stripList(split(text,'\n\n'))
        for i in range(len(paragraphs)):
            p = paragraphs[i]
            indent = len(p) - len(lstrip(p))
            #if indent or p[0] == '>': continue
            if indent: continue
            m = re.match(r'^[>\s]+',p)
            if m:
                prefix = m.group()
                p = re.sub(r'(?m)^'+prefix,'',p)
            else:
                prefix = ''
            # TextFormatter loses a trailing newline
            # (and a single leading newline, but that shouldn't apply)
            if p[-1] == '\n': nl = '\n'
            else: nl = ''
            p = TextFormatter([{'width':70-len(prefix),
                                'margin':0,
                                'fill':1,
                                'pad':0}]).compose([p])
            p = re.sub(r'(?m)^',prefix,p)
            p += nl
            paragraphs[i] = p
            
        text = join(paragraphs,'\n\n')

        # strip leading newlines
        text = re.sub(r'(?s)^\n+',r'',text)
        # strip trailing newlines
        text = re.sub(r'(?s)\n+$',r'\n',text)
        # lose any html quoting
        text = html_unquote(text)
        return text

#if __name__ == '__main__':
#    import contract, doctest, Mail
#    contract.checkmod(Mail)
#    doctest.testmod(mid)
