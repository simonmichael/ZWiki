# WikiForNow-style regulations
#
# NB this is unused, has bitrotted, and will be removed soon
# unless I see a good reason to keep it in

#import string, re
#import Permissions
#import Globals
#from AccessControl import ClassSecurityInfo
#import Acquisition
#from Persistence import Persistent
#from Utils import flatten
#
#default_regs = {                        # regulations stuff
#    'create': 'nonanon',
#    'edit': 'nonanon',
#    'comment': 'nonanon',
#    'move': 'owners',
#    }
#
#class RegulationsSupport:
#    """
#    mix-in class to support WikiForNow-style ownership & regulations
#
#    RESPONSIBILITIES
#    - 
#    - 
#    - 
#    -
#
#    see also ZWikiRegulations below
#    """
#    _regs = None
#    #_properties=(
#    #    {'id':'subscriber_list', 'type': 'lines', 'mode': 'w'},
#    #    )
#
#    security = ClassSecurityInfo()
#    set = security.setPermissionDefault
#    set(Permissions.ChangeRegs, ('Owner', 'Manager'))
#    set = None
#
#    ######################################################################
#    # misc methods
#
#    security.declarePublic('usingRegulations')
#    def usingRegulations(self):
#        """
#        are we using WFN-style regulations in this wiki ?
#        """
#        return 0
#        #if getattr(self.folder(),'use_regulations',0): return 1
#        #else: return 0
#
#    def _setOwnerRole(self, REQUEST=None):
#        """
#        Add the 'Owner' local role to self according to
#        regulations.subOwner of origin page.
#        """
#        who = {}
#        so = REQUEST.get('who_owns_subs', 'creator')
#        if so in ['creator', 'both']:
#            who[REQUEST.AUTHENTICATED_USER.getUserName()] = None
#        if so in ['original_owner', 'both']:
#            for k, r in self.get_local_roles():
#                if 'Owner' in r: who[k] = None
#        if who:
#            for i in who.keys():
#                self.manage_addLocalRoles(i, ['Owner'])
#        else:
#            self.manage_addLocalRoles(
#                REQUEST.AUTHENTICATED_USER.getUserName(),
#                ['Owner'])
#
#    security.declarePublic('page_owners')
#    def page_owners(self, limit=None):
#        """Return a list of users with Owner role in wiki page."""
#        got = []
#        for k, v in self.get_local_roles():
#            if 'Owner' in v and k not in got:
#                got.append(k)
#                if limit and len(got) > limit:
#                    got.append('...')
#                    return got
#        return got
#    security.declarePublic('isAllowed')
#    def isAllowed(self, op, REQUEST=None):
#        """See ZWikiRegulations.isAllowed """
#        return self._getRegs().isAllowed(op, REQUEST=REQUEST)
#    security.declarePublic('subOwner')
#    def subOwner(self):
#        """Identify who gets ownership of pages created from this page."""
#        return self._getRegs().subOwner()
#    security.declarePublic('isRegSetter')
#    def isRegSetter(self, REQUEST, new=0):
#        """User is among those allowed to set the regulations for curr page.
#
#        If 'new' is true, then the computation is for the user as creator of a
#        new page, from the current page."""
#        # XXX klm: For new pages, we have to look at how subownership is
#        #          passed.  It's interesting that this, in itself, means we
#        #          can't use the permissions mechanism, since the user need
#        #          not yet have the role against which to measure.
#        user = REQUEST.AUTHENTICATED_USER
#        # XXX klm: We might should allow *anyone* if *noone* has owner role!
#        if user.has_permission(Permissions.ChangeRegs, self):
#            # A sure bet, whether or not we're talking about a new page.
#            return 1
#        elif new:
#            # If the current page dictates that the creator gets ownership,
#            # then they'll get the permission.  The prior case handles the
#            # situation where the user has permissions regardless of
#            # ownership.
#            return self.subOwner() in ['creator', 'both']
#        return 0
#
#    security.declareProtected(Permissions.ChangeRegs, 'setRegulations')
#    # added new argument here for create().. don't see how it worked without
#    def setRegulations(self, REQUEST, new=0):
#        """See ZWikiRegulations.set """
#        if not self.isRegSetter(REQUEST,new):
#            raise 'Unauthorized', ('You are not allowed to set ZWiki page '
#                                   'regulations in this folder.')
#        r = self._getRegs()
#        offspring = None
#        for op in self.regOps():
#            un = REQUEST.get(op + '-usernames', None)
#            cat = REQUEST.get(op + '-category', None)
#            r.setOp(op, un, cat)
#            # Propagate to subpages if desired
#            if "ON" == REQUEST.get('propagate-' + op, None):
#                folder = self._my_folder()
#                if offspring is None:
#                    #nesting = WikiNesting(self._my_folder())
#                    #offspring = flatten(nesting.get_offspring([self.id()]))
#                    offspring = flatten(self.getOffspringNesting([self.pageName()]))
#                    offspring.remove(self.pageName())
#                for sub in offspring:
#                    subobj = folder[sub]
#                    if subobj.isRegSetter(REQUEST):
#                        subobj._getRegs().setOp(op, un, cat)
#        r.setSubOwner(REQUEST.get('who_owns_subs', None))
#        self._setRegs(r)
#    security.declarePublic('regOps')
#    def regOps(self):
#        """See ZWikiRegulations.ops """
#        return self._getRegs().ops()
#    security.declarePublic('regCategories')
#    def regCategories(self):
#        """See ZWikiRegulations.categories"""
#        return self._getRegs().categories()
#    security.declarePublic('opCategory')
#    def opCategory(self, op):
#        """See ZWikiRegulations.opCategory"""
#        return self._getRegs().opCategory(op)
#    security.declarePublic('opUsernames')
#    def opUsernames(self, op):
#        """See ZWikiRegulations.opUsernames"""
#        return self._getRegs().opUsernames(op)
#    security.declarePublic('adoptRegulationsFrom')
#    def adoptRegulationsFrom(self, other):
#        """See ZWikiRegulations.adoptRegulationsFrom"""
#        return self._getRegs().adoptRegulationsFrom(other)
#    def _getRegs(self, betweens=None):
#        """Fetch the regulations - making sure they're instantiated.
#
#        Optional 'betweens' arg is for internal use in detecting and avoiding
#        parenting loops."""
#        # XXX klm: The "if r is None" stuff is to retrofit
#        #          initialization of the _regs delegate to the ZWikiPage
#        #          instances.  Not ideal, but good enough for now..
#        r = self._regs
#        if r is None:
#            r = ZWikiRegulations(page=self, betweens=betweens)
#        return r
#    def _setRegs(self, r):
#        # klm: Something a bit funky, for dealing with legacy (pre-regs)
#        #      ZWiki pages.  We provide transient regs for reads on these
#        #      legacy pages, which we dare not write - else the reader may
#        #      take ownership of those object, improperly.  They will,
#        #      consequently, be regenerated again and again, until the page
#        #      is written.  New, post-regs pages will get permanent regs
#        #      structures when created...
#        self._regs = r
#        self._p_changed = 1
#    def _my_folder(self):
#        """
#        Obtain parent folder.
#        """
#        #don't acquire regs from other folders.
#        #return self.folder().aq_base
#        return self.folder()
#
#Globals.InitializeClass(RegulationsSupport) # install permissions
#
#
#
#class ZWikiRegulations(Persistent, Acquisition.Implicit):
#    """
#    Keep track of who can do what with a wiki page.
#
#    In contrast to permissions, ZWikiRegulations control a narrow set of
#    operations according to a small set of roles categories combined with
#    explicitly designated users.
#
#    The operations are:
#
#     - create
#     - edit
#     - comment
#     - move (rename/delete/reparent)
#
#    The role categories are progressively more broad, with successive
#    categories containing their predecessors:
#
#     - nobody - not even owners (but owners or managers can change the policy)
#     - owners - users with 'Owner' role, or page ownership
#     - nonanon - everyone but anonymous user
#     - everyone - anyone including anonymous.
#     """
#    _page = None
#    _ops_seq = ('create', 'edit', 'comment', 'move')
#    _categories_seq = ('nobody', 'owners', 'nonanon', 'everyone')
#    _subowners_seq = ('creator', 'original_owner', 'both')
#    _subowner = 'both'
#
#    def __init__(self, page=None, betweens=None,
#                 edit=None, move=None, create=None, comment=None):
#        # The class has an interesting (read, not ideal) provision for
#        # defaulting the regulations for new regulation instances.  It is
#        # purely a legacy provision - it only happens when regulations are
#        # instantiated for already-existing pages.  They first try to obtain a 
#        # copy of the regulations of the parent page, then try for the
#        # FrontPage of the Wiki, and failing to find one there, uses a canned
#        # spec.
#        # 
#        # Also, legacy pages will get new regulation objects on *reads*, and
#        # we must avoid writing the new regulations on reads, or the new
#        # object will be owned by the reader, who may not have or grant read
#        # privileges to other readers.  To avoid problems, we don't write the
#        # defaulted values until an explicit WikiPage write - which means we
#        # redefault again and again, sigh.
#
#        self._page = page
#        got_defaults = 0
#        self._vs_category = {}
#        self._vs_username = {}
#        if hasattr(page, 'id') and page.id() != 'FrontPage':
#            # Try to adopt regulations from ancestors, or FrontPage.
#            superior = None
#            for i in page.parents:
#                if hasattr(page._my_folder(), i):
#                    superior = page._my_folder()[i]
#                    if (not betweens) or (superior.aq_base not in betweens):
#                        break
#                    else:
#                        # Whoops - we're recursing to ourself through a
#                        # parenting loop.  Skip this one.
#                        superior = None
#            if superior is None and hasattr(page._my_folder(), 'FrontPage'):
#                superior = page._my_folder()['FrontPage']
#            if superior is not None:
#                got_defaults = self.adoptRegulationsFrom(superior,
#                                                         betweens=betweens)
#        if not got_defaults:
#            self._use_defaults(edit=edit, move=move,
#                               create=create, comment=comment)
#    def _use_defaults(self, edit=None, move=None, create=None, comment=None):
#        "When unable to find others to adopt, use canned 'default_regs'."
#        if edit is None: edit = default_regs['edit']
#        if create is None: create = default_regs['create']
#        if move is None: move = default_regs['move']
#        if comment is None: comment = default_regs['comment']
#        self._vs_category = {'create': create,
#                             'edit': edit,
#                             'comment': comment,
#                             'move': move,
#                             }
#        self._vs_username = {'create': [],
#                             'edit': [],
#                             'comment': [],
#                             'move': [],
#                             }
#    def _user_qualifies(self, user, operation=None, category=None):
#        """Return true if user is allowed to do operation or fits category."""
#        if ((category is None and operation is None)
#            or (category is not None and operation is not None)):
#            raise ValueError, ("One of operation or category "
#                               "must be specified.")
#        if category is None:
#            category = self._vs_category[operation]
#        if category == 'everyone':
#            return 1
#        elif category == 'anyone':
#            return 1
#        elif category == 'nonanon':
#            if hasattr(user.acl_users, '_nobody'):
#                baseuser = ((hasattr(user, 'aq_base') and user.aq_base)
#                            or user)
#                anon = user.acl_users._nobody
#                baseanon = ((hasattr(anon, 'aq_base') and anon.aq_base)
#                            or anon)
#                return baseuser != baseanon
#            else:
#                return user.getUserName() != 'Anonymous User'
#        elif category == 'owners':
#            # Users with 'Owner' role
#            return ((self._page.getOwner() is user)
#                    or ('Owner' in user.getRolesInContext(self._page)))
#        elif category == 'nobody':
#            return 0
#        else:
#            raise SystemError, ("Unrecognized role category '%s' "
#                                "for operation '%s'"
#                                % (category, operation))
#        
#    def subOwner(self):
#        """Identify who gets ownership of pages created from this page."""
#        return self._subowner
#    def isAllowed(self, op, REQUEST=None, user=None):
#        """Query whether operation is enabled for REQUEST user."""
#        if user is None and REQUEST is not None:
#            user = REQUEST.AUTHENTICATED_USER
#        username = user.getUserName()
#        return ((username in self._vs_username[op])
#                or self._user_qualifies(user, operation=op))
#    def setOp(self, op, usernames, category):
#        """Set who can do a particular operation."""
#        if category is not None:
#            self._vs_category[op] = category
#            self._p_changed = 1
#        if usernames is not None:
#            self._vs_username[op] = usernames
#            self._p_changed = 1
#    def setSubOwner(self, which):
#        """Set how owner role of pages created from this page is determined.
#        Which must be one of:
#         - 'creator': person doing the page creation.
#         - 'original_owner': parties that have owner role for this page.
#         - 'both': includes both 'original_owner' and 'creator'."""
#        if which is None: return
#        elif which in self._subowners_seq:
#            self._subowner = which
#        else:
#            raise ValueError, ("Subowner setting must be one of %s, not '%s'"
#                               % (_subowners_seq, which))
#    def ops(self):
#        return self._ops_seq
#    def categories(self):
#        return self._categories_seq
#    def opCategory(self, op):
#        """Return category setting for specified operation."""
#        return self._vs_category[op]
#    def opUsernames(self, op):
#        """Return category setting for specified operation."""
#        return tuple(self._vs_username[op])
#    def adoptRegulationsFrom(self, other, betweens=None):
#        """Take on the regulations of another (presumably, parent) page.
#
#        We return 1 if successful, else 0, eg we're in a parenting
#        loop, with no member from which to adopt.
#
#        Optional 'betweens' arg is for internal use in detecting and avoiding
#        parenting loops."""
#        self._p_changed = 1
#        if betweens and self._page.aq_base in betweens:
#            # We're in a parenting loop - bail out, but with
#            # self._p_changed set so defaults are instituted in the page.
#            return 0
#        if not betweens: betweens = [self._page.aq_base]
#        else: betweens.append(self._page.aq_base)
#        r = other._getRegs(betweens=betweens)
#        if r is None:
#            return
#        self._subowner = r._subowner
#        for k, v in r._vs_category.items():
#            self._vs_category[k] = v
#        for k, v in r._vs_username.items():
#            self._vs_username[k] = v[:]
#        return 1
#    def __repr__(self):
#        pgid = ((self._page is None) and None) or self._page.id()
#        return ("<%s of %s at 0x%s>"
#                % (self.__class__.__name__, pgid, hex(id(self))[2:]))

