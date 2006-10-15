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

from types import *
import string, re
import email
from email.Message import Message
from email.Utils import parseaddr, getaddresses
from email.Iterators import typed_subpart_iterator

from Products.ZWiki.Regexps import wikiname1,wikiname2,bracketedexpr,urlchars
from Products.ZWiki.Utils import BLATHER
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
        BLATHER('mailin.py processing incoming message:\n%s' % message)
        #BLATHER('mailin.py processing incoming message')
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

        # raises an exception if there's no text part
        try:
            plaintextpart = typed_subpart_iterator(self.msg,
                                                   'text',
                                                   'plain').next().get_payload(decode=1)
        except StopIteration:
            plaintextpart = ''
        self.body = self.cleanupBody(plaintextpart)
        
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
        if hasattr(self.folder(),'banned_links'):
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
                while not hasattr(folder.aq_base,'banned_links'):
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
        # strip Bob's signature
        body = self.stripSignature(body)
        # strip TBC (typical bloody citations)
        #body = re.sub(
        #    r'(?si)----- ?message d\'origine.*',r'',body)
        #body = re.sub(
        #    r'(?si)----- ?original message.*',r'',body)
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
            self.destpage = self.workingpage = self.context
            self.destpagename = self.destpage.pageName()
            self.newpage = self.trackerissue = 0
            self.checkMailinAllowed()
            return

        # posting in wiki folder context (the normal case)
        # find a page to work from
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
    # use the time of sending, or the time of posting to the wiki - see
    # how the latter works out
    # mailing list support: when a list and wiki are mutually subscribed,
    # and a mail comes in from the list, we want to forward it out to all
    # subscribers except the list, which has done it's own delivery.
    # Some lists will detect the duplicate automatically, for others we
    # expect the X-BeenThere header and tell zwiki to exclude that address.
    m.destpage.comment(text=m.body,
                       username=m.FromUserName,
                       REQUEST=self.REQUEST,
                       subject_heading=subjectPrefix+subject,
                       exclude_address=m.xbeenthere,
                       message_id=m.messageid,
                       in_reply_to=m.inreplyto
                       )
    return None
