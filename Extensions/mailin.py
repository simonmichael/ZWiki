"""
zwiki mailin - post an incoming email message to a wiki

This is an external method for receiving mail from a mailer alias,
procmail recipe or script via something like:
| curl -n -F 'msg=<-' http://mysite/mywikifolder/mailin
and posting it to a suitable zwiki page.  It expects at least one
argument, a message in RFC2822 format.

Here are the delivery rules:
XXX see the latest CHANGES.txt for some updates to these.

- if the message appears to be a zwiki mailout or from an auto-responder
  or junk, silently discard it

- if called in a page context (http://site/wikipage/mailin), always use
  that page. Otherwise,

- (DISABLED: if a recipient of the form
  ".*(wiki|mailin|tracker|bugs|issues)@virtualhost" (MAILINADDREXP) is
  found, where virtualhost matches an existing VirtualHostMonster entry,
  then in the corresponding folder, otherwise,)

- in the current folder (which must contain at least one zwiki page),

- unless called with subscribersonly=0 or the folder's mailin_policy
  property is 'open' (old posting_policy property also supported), check
  that the sender (From or Sender address) is subscribed somewhere in the
  wiki; or, is listed in the mail_accept_nonmembers property. If not,
  bounce the message.

- decide which of the recipients is us, as follows:

   1. if there's only one, use that one
   2. or the first one whose address matches the folder's mail_from property
   3. or the first one whose address matches MAILINADDREXP
   4. or the first one

  NB cases 3 and 4 may sometimes lead it to guess the wrong recipient and
  potentially deliver to the wrong page. Perhaps we can get this from the
  mail servers and pass it as an argument.

- if called with trackerissue=1 or the recipient matches
  ".*(tracker|bugs|issues)@" (TRACKERADDREXP), create a tracker issue page.

- Otherwise, look for

   1. a non-empty page name in the recipient real name (PAGEINREALNAMEEXP)
   2. or the first WikiName or [bracketed name] in the subject
   3. or the folder's default_page property (possibly acquired)
   4. or the defaultpage argument we were called with (XXX remove ?)
   5. or the DEFAULTPAGE defined below
   6. or the first zwiki page in the folder (as returned by objectValues)

- and add a comment to that page, creating it if necessary.

Note page creation and comments will trigger subscriber mail-outs as usual.

todo:
refactor
size limits
friendly bounce messages

"""

from types import *
import string, re
import email
from email.Message import Message
from email.Utils import parseaddr, getaddresses
from email.Iterators import typed_subpart_iterator

from Products.ZWiki.Regexps import wikiname1,wikiname2,bracketedexpr
from Products.ZWiki.Utils import BLATHER

# which page should be used when there is no bracketed page name in the subject
DEFAULTMAILINPAGE = None 
#PAGEINSUBJECTEXP = r'(%s|%s)' % (wikiname1,wikiname2)
#PAGEINSUBJECTEXP = r'(%s|%s|%s)' % (wikiname1,wikiname2,bracketedexpr)
PAGEINSUBJECTEXP = bracketedexpr
MAILINADDREXP = r'(wiki|mailin|tracker|bugs|issues)@'
TRACKERADDREXP = r'(tracker|bugs|issues)@'
# extract a page name from the recipient real name
# because different things show up here - 'name', mail address, etc. -
# we recognize only page names beginning and ending with a word character
# and not containing @
PAGEINREALNAMEEXP = r'(?=^[^@]*$).*?(?P<page>\w.*\w)' 
MAX_SIGNATURE_STRIP_SIZE = 500


def isJunk(msgtext):
    """
    Return true if this message should be silently ignored.

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
    return 0


class MailIn:
    """
    I represent an incoming mail message being posted to a wiki folder.

    I parse the incoming rfc2822 message string and expose the parts of
    interest, and (given a wiki context) figure out how to deliver myself
    as per the zwiki delivery rules above.
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
                 defaultpage=DEFAULTMAILINPAGE,
                 subscribersonly=1,
                 trackerissue=0,
                 checkrecipient=0,
                 checksubject=1,
                 ):
        BLATHER('mailin.py: processing incoming message:\n%s' % message)
        self.context = context
        self.defaultpage = defaultpage
        self.subscribersonly = subscribersonly
        self.trackerissue = trackerissue
        self.checkrecipient = checkrecipient
        self.checksubject = checksubject
        self.msg = email.message_from_string(message)
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

        plaintextpart = typed_subpart_iterator(self.msg,
                                               'text',
                                               'plain').next().get_payload()
        self.body = self.cleanupBody(plaintextpart)
        
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
        The message recipient that was used for delivery here (an email tuple).

        The recipient helps determine the mailin action; if there are
        several, we need to find out which one refers to the wiki.  We'll
        use the folder's mail_from property as a hint, or guess if we have
        to. 
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

    def workingPage(self):
        """
        A wiki page object which we can use for further operations. tricksy XXX
        """
        pass
        
    def defaultMailinPage(self):
        """
        The default wiki page for receiving mailins. May be None.
        """
        pass
        
    def decideDestination(self):
        """
        Figure out what wiki page this mail-in should go to.

        Fairly involved calculations trying to figure out what to do in a
        robust way. Sets self.destpage, self.destpagename, self.newpage,
        self.trackerissue, or sets a message in self.error if it can't.
        
        """
        if self.contextIsPage():
            self.destpage = self.workingpage = self.context
            self.destpagename = self.destpage.title_or_id()
            self.newpage = self.trackerissue = 0
            return

        # posting in wiki folder context (the normal case)

        # find the default mailin page if any
        # note this is now different from the default_page folder property
        #defaultpagename = getattr(self.folder(),'default_page',self.defaultpage)
        defaultpagename = self.defaultpage

        # find a preliminary working page
        #self.workingpage = self.workingPage()
        if defaultpagename:
            self.workingpage = getattr(self.folder(),defaultpagename,None)
        if not self.workingpage:
            allpages = self.folder().objectValues(spec='ZWiki Page')
            if allpages:
                firstpage = allpages[0]
                self.workingpage = \
                    firstpage.pageWithName(defaultpagename) or firstpage
        if not self.workingpage:
            BLATHER('mailin.py: could not find a working page')
            self.error = '\nSorry, I could not find an existing wiki page to work with.\n\n\n'
            return
        # update defaultpagename if it was wrong
        defaultpagename = self.workingpage.title_or_id()

        # find the destination page
        # look for a page name
        # in the recipient's real name part if enabled..
        if self.checkrecipient:
            m = re.search(PAGEINREALNAMEEXP,self.recipient()[0])
            if m:
                self.destpagename = m.group('page')
        # or in the subject if enabled.. (default)
        if (not self.destpagename) and self.checksubject:
            matches = re.findall(PAGEINSUBJECTEXP,self.subject)
            if matches:
                self.destpagename = matches[-1] # use rightmost
                # strip enclosing []'s
                self.destpagename = re.sub(bracketedexpr, r'\1',self.destpagename)

        # or use the default mailin page if any..
        if (not self.destpagename) and self.defaultpage:
            self.destpagename = defaultpagename

        # now, either we have identified an existing destination page
        # (fuzzy naming allowed)..
        page = (self.destpagename and
                self.workingpage.pageWithFuzzyName(self.destpagename,
                                                   ignore_case=1))
        if page:
            # also change working page to get right parentage etc.
            self.destpage = self.workingpage = page
            self.destpagename = self.destpage.title_or_id()
        # or we have the name of a new page to create
        elif self.destpagename:
            self.newpage = 1
        # or we are creating a tracker issue, which doesn't need a name
        elif (self.trackerissue or re.search(TRACKERADDREXP,self.recipient()[1])):
            self.trackerissue = 1
        # or we discard this message
        else:
            self.error = '\nMessage had no destination page, ignored.\n\n\n'
            BLATHER('mailin.py: message had no destination page, ignored')

        return

    def checkMailinAllowed(self):
        """
        Check if the mailin determined by decideDestination() is permitted.

        Is the sender allowed to mail in here ?
        - if open posting is allowed, we'll accept anybody.
        - otherwise they must be a subscriber somewhere in the wiki
        - or be listed in the mail_accept_nonmembers property
          (useful to allow mailing lists, etc)
        Set self.error if not permitted.
        """
        postingpolicy = getattr(self.folder(),'mailin_policy',
                                # backwards compatibility
                                getattr(self.folder(),'posting_policy',None)) 
        accept = getattr(self.folder(),'mail_accept_nonmembers',[])
        if (not self.subscribersonly or
            postingpolicy == 'open' or
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


def mailin(self,
           msg,
           pagenameexp=None, #XXX temporary backwards compatibility
           defaultpage=DEFAULTMAILINPAGE,
           separator=None, #XXX temporary backwards compatibility
           checkrecipient=0,
           checksubject=1,
           trackerissue=0,
           subscribersonly=1,
           ):
    context = self
    # these come over the web as strings
    checkrecipient  = int(checkrecipient or 0)
    checksubject    = int(checksubject or 0)
    trackerissue    = int(trackerissue or 0)
    subscribersonly = int(subscribersonly or 0)

    # silently discard any junk before doing anything else
    if isJunk(msg): return

    # parse and figure out how to deliver the message
    m = MailIn(context,
               msg,
               defaultpage=defaultpage,
               subscribersonly=subscribersonly,
               trackerissue=trackerissue,
               checkrecipient=checkrecipient,
               checksubject=checksubject,
               )
    m.decideDestination()
    m.checkMailinAllowed()
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
        #BLATHER('mailin.py: created '+m.destpagename)

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
                                                 REQUEST=self.REQUEST,
                                                 sendmail=0)
        m.destpage = m.workingpage.pageWithName(pagename)
        subjectPrefix = '(new) '
        #BLATHER('mailin.py: created issue '+subject)

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
    #BLATHER('mailin.py: commented on '+m.destpagename)
