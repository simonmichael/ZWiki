# Zwiki/zwiki.org makefile

# Zwiki release reminders
# -----------------------
# check for unrecorded changes
# check for translations
# check tests pass
# check for late tracker issues
# check README,wikis/,skins/,zwiki.org HelpPage,QuickReference
# darcs changes --from-tag NN into CHANGES & edit; don't add header at top
# update version.txt
# make release
# test restart server
# announce
#  copy CHANGES to ReleaseNotes
#  check FrontPage, KnownIssues, OldKnownIssues
#  #zwiki, zwiki@zwiki.org (rc)
#  #zwiki, zwiki@zwiki.org, zope-announce@zope.org (final)

PRODUCT=ZWiki
HOST=zwiki.org
REPO=$(HOST):/repos/$(PRODUCT)
RSYNCPATH=$(HOST):/repos/$(PRODUCT)
LHOST=localhost:8080
CURL=curl -o.curllog -sS -n


default: test


## docs

docs: doxygen epydoc

doxygen:
	rm -rf doc/doxygen/*
	doxygen doxygen.conf

epydoc:
	rm -rf doc/epydoc/*
	epydoc --parse-only --exclude='_tests' --docformat=restructuredtext -o doc/epydoc --name=Zwiki --url=http://zwiki.org --graph=all .



## i18n

# TRANSLATION UPDATE PROCEDURE
# ----------------------------
# translators update translations through launchpad, any time
# developers update and upload pot files, any time
# release manager, before release:
#  updates and uploads pot files
#   make pot, record
#   https://translations.launchpad.net/zwiki/trunk/+pots/zwiki/+upload
#   wait for upload
#    https://translations.launchpad.net/zwiki/trunk/+imports
#  downloads and records po files
#   https://translations.launchpad.net/zwiki/trunk/+pots/zwiki
#   https://translations.launchpad.net/zwiki/trunk/+pots/zwiki-plone
#   use download links in mail, unpack to i18n/new/
#    curl -s http://launchpadlibrarian.net/11807388/launchpad-export.tar.gz -o launchpad.tar.gz
#    curl -s http://launchpadlibrarian.net/11807673/launchpad-export.tar.gz -o launchpad-plone.tar.gz
#   check for new languages, darcs wh -sl i18n
#   make po, record
#  re-uploads po files to update status bars..
#   make poupload
#   https://translations.launchpad.net/zwiki/trunk/+pots/zwiki/+upload
#   wait for upload
#    https://translations.launchpad.net/zwiki/trunk/+imports
#
# PROBLEMS
#  launchpad strips out some #. Default lines ? need them ?
#  zwiki-plone.pot complicates, figure out how to simplify

LANGUAGES=af ar de en_GB es et fi fr he hu it ja nl pl pt pt_BR ro ru sv th tr zh_CN zh_TW #fr_CA ga

# requires 18ndude >= 2008/02/06
pot:
	echo '<div i18n:domain="zwiki">' >skins/dtmlmessages.pt # dtml extraction hack
	find plugins skins wikis -name "*dtml" | xargs perl -n -e '/<dtml-translate domain="?zwiki"?>(.*?)<\/dtml-translate>/ and print "<span i18n:translate=\"\">$$1<\/span>\n";' >>skins/dtmlmessages.pt                           #
	echo '</div>' >>skins/dtmlmessages.pt                   #
	i18ndude rebuild-pot --pot i18n/tmp.pot --create zwiki --exclude="_darcs" .
	echo '# Gettext message file for Zwiki' >i18n/zwiki.pot
	tail +4 i18n/tmp.pot >>i18n/zwiki.pot
	rm -f i18n/tmp.pot
	rm -f skins/dtmlmessages.pt                             #

# tar up pot & po files for upload to launchpad
poupload:
	cd i18n; \
	rm -f zwiki.tar.gz; \
	tar cvf zwiki.tar zwiki.pot; \
	for L in $(LANGUAGES); do tar rvf zwiki.tar $$L.po; done; \
	tar rvf zwiki.tar zwiki-plone.pot; \
	for L in $(LANGUAGES); do tar rvf zwiki.tar plone-$$L.po; done; \
	gzip -f zwiki.tar; 

# unpack po files downloaded from launchpad
po:
	cd i18n; \
  rm -rf new; \
  mkdir new; \
  tar xzvf launchpad.tar.gz -C new; \
  tar xzvf launchpad-plone.tar.gz -C new; \
	for L in $(LANGUAGES); do \
	 mv new/zwiki/zwiki-$$L.po $$L.po; \
	 mv new/i18n/zwiki-plone-$$L.po plone-$$L.po; \
	 done

postats:
	cd i18n; \
	for L in $(LANGUAGES); do \
	 echo $$L; \
	 msgfmt --statistics $$L.po -o zwiki-$$L.mo; \
	 msgfmt --statistics plone-$$L.po -o zwiki-plone-$$L.mo; \
	 done; \
	rm -f *.mo



## testing

# To run Zwiki unit tests: install Zope 2.10, adjust INSTANCE paths,
# install or link your ZWiki directory in $INSTANCE/Products.
# Some additional tests will run if Plone is installed.
# minimal products, fast startup
INSTANCE=/zope2
# all products
BIGINSTANCE=/zope1

# we keep zwiki's tests in *_tests.py alongside the code
ZWIKITESTS=--tests-pattern='_tests$$' --test-file-pattern='_tests$$'

# run tests as quickly as possible
TEST=$(INSTANCE)/bin/zopectl test $(ZWIKITESTS) --keepbytecode -v #--nowarnings

# run all tests verbosely and thoroughly
TESTALL=$(BIGINSTANCE)/bin/zopectl test $(ZWIKITESTS) -a 3 -vv

test:
	$(TEST) -m Products.ZWiki

testall:
	$(TESTALL) -m Products.ZWiki

# test one module (or all matching modules):
#   make testmod-Mail
# in a subdirectory:
#   make testmod-Extensions.Install
# with additional testrunner args:
#   make testmod-"pagetypes.rst -vv -D"
testmod-%:
	$(TEST) -m Products.ZWiki.$*

# test one test (or all matching tests):
#   make test-test_install
test-%:
	$(TEST) -m Products.ZWiki -t $*

# as above, but just make testmethodname:
#   make test_install
test_%:
	$(TEST) -m Products.ZWiki -t $@

# silliness to properly capture output of a test run
TESTRESULTS=TESTRESULTS
testresults:
	date >$(TESTRESULTS)
	make -s test >>$(TESTRESULTS) 2>.stderr
	cat .stderr >>$(TESTRESULTS)
	rm -f .stderr

testhelp:
	$(INSTANCE)/bin/zopectl test --help



## release

VERSION:=$(shell cut -c7- version.txt )
MAJORVERSION:=$(shell echo $(VERSION) | sed -e's/-[^-]*$$//')
VERSIONNO:=$(shell echo $(VERSION) | sed -e's/-/./g')
FILE:=$(PRODUCT)-$(VERSIONNO).tgz

release: releasenotes version releasetag tarball push rpush

releasenotes:
	@echo recording release notes
	@darcs record -am 'release notes' CHANGES

# bump version number in various places and record; don't have other
# changes in these files
version:
	@echo bumping version to $(VERSIONNO)
	@(echo 'Zwiki' $(VERSIONNO) `date +%Y/%m/%d`; echo '======================='; echo)|cat - CHANGES \
	  >.temp; mv .temp CHANGES
	@perl -pi -e "s/__version__='.*?'/__version__='$(VERSIONNO)'/" \
	  __init__.py
	@perl -pi -e "s/Zwiki version [0-9a-z.-]+/Zwiki version $(VERSIONNO)/"\
	  skins/zwiki/HelpPage.stx
	@darcs record -am 'bump version to $(VERSIONNO)' \
	  version.txt CHANGES __init__.py skins/zwiki/HelpPage.stx

releasetag:
	@echo tagging release-$(VERSION)
	darcs tag --checkpoint -m release-$(VERSION)

# always puts tarball in mainbranch/releases
# look at darcs dist
tarball: clean
	@echo building $(FILE) tarball
	@cp -r _darcs/current $(PRODUCT)
	@tar -czvf releases/$(FILE) $(PRODUCT)
	@rm -rf $(PRODUCT)



## misc. syncing

rcheck:
	rsync -ruvC -e ssh -n releases $(RSYNCPATH)

rpush:
	rsync -ruvC -e ssh releases $(RSYNCPATH)

check:
	darcs whatsnew --summary

push:
	darcs push -v -a $(REPO)

push-exp:
	darcs push -v -a $(HOST):/repos/$(PRODUCT)-exp

pull-simon pull:
	darcs pull --interactive -v http://zwiki.org/repos/ZWiki

pull-lele:
	darcs pull --interactive -v http://nautilus.homeip.net/~lele/projects/ZWiki

pull-bob:
	darcs pull --interactive -v http://bob.mcelrath.org/darcs/zwiki

pull-bobtest:
	darcs pull --interactive -v http://bob.mcelrath.org/darcs/zwiki-testing

pull-bill:
	darcs pull --interactive -v http://page.axiom-developer.org/repository/ZWiki

getproducts:
	cd /zope2/Products; \
	  rsync -rl --progress --exclude="*.pyc" zwiki.org:/zope2/Products .



# misc

tags: xctags

# to make a good tag file, get exuberant ctags
XCTAGS=ctags -eR --langmap=python:+.cpy.vpy,c:+.css,html:+.pt.cpt.dtml.xml.zcml
xctags:
	$(XCTAGS) --exclude=@.tagsexclude * || $(XCTAGS) *

# old way
etags:
	find $$PWD/ -name '*.py' -o  -name '*dtml' -o -name '*.pt' \
	  -o -name '*.css' -o -name '*.pot' -o -name '*.po' \
	  -o -name _darcs  -prune -type f \
	  -o -name old     -prune -type f \
	  -o -name doc     -prune -type f \
	  | xargs etags

zopetags:
	cd /zope/lib/python; \
	  ~/bin/eptags.py `find $$PWD/ -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

producttags:
	cd /zope2/Products; \
	  ~/bin/eptags.py `find $$PWD/ -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
	     -o -name old -o -name .old    -prune -type f `

plonetags:
	cd /zope2/Products/CMFPlone; \
	  ~/bin/eptags.py \
	  `find $$PWD/ -name '*.py' -o -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

alltags: tags producttags zopetags
	cat TAGS /zope2/Products/TAGS /zope/lib/python/TAGS >TAGS.all

linecounts:
	wc -l `ls *.py |grep -v _tests` |sort -nr >LINECOUNTS

PYFILES=*.py [A-Za-z]*/*.py [A-Za-z]*/*/*.py [A-Za-z]*/*/*/*.py
pyflakes:
	pyflakes $(PYFILES)

clean:
	rm -f .*~ *~ *.tgz *.bak *.hi *.ho `find . -name "*.pyc"`

Clean: clean
	rm -f i18n/*.mo skins/dtmlmessages.pt

# ensure all files in zwiki.org repo have the right permissions for all
# users, darcs mail-in etc. Everything should have group "zwiki", be
# group-writable, and directories should have the setgid bit set.
# May need to run this periodically since certain operations mess up
# the permissions, such as... (?)
# Run as superuser in the ZWiki dir on zwiki.org.
fixperms:
	chgrp -R zwiki *
	chmod -R ug+rw *
	find . -type d -exec chmod g+s {}  \;


# misc automation examples

refresh-%.po:
	@echo refreshing $(PRODUCT) $*.po file on $(HOST)
	@$(CURL) 'http://$(HOST)/Control_Panel/TranslationService/ZWiki.i18n-$*.po/reload'

refresh: refresh-$(PRODUCT)

refresh-%:
	@echo refreshing $* product on $(HOST)
	@$(CURL) 'http://$(HOST)/Control_Panel/Products/$*/manage_performRefresh'

refresh-mailin:
	@echo refreshing mailin.py external method on $(HOST)
	@$(CURL) 'http://$(HOST)/mailin/manage_edit?id=mailin&module=mailin&function=mailin&title='

lrefresh: lrefresh-$(PRODUCT)

lrefresh-%:
	@echo refreshing product $* on $(LHOST)
	curl -n -sS -o.curllog 'http://$(LHOST)/Control_Panel/Products/$*/manage_performRefresh'

SITES=zwiki.org zopewiki.org plone.demo.zwiki.org
THREADS=2 # same as in zope.conf
LOADALL=ab -n$(THREADS) -c$(THREADS)

warm-zodb-cache warm:
	for site in $(SITES); do \
	  $(LOADALL) "http://$$site/TestPage/recentchanges?period=ever&summaries=on"; \
	  $(LOADALL) "http://$$site/TestPage/searchwiki?expr="; \
          done
	$(LOADALL) http://zwiki.org/RecycleBin
	$(LOADALL) http://zwiki.org/FileUploads

# fun.. darcs-style author stats. Need to make this easier.
authorstats:
	@make -s list_authors && ./list_authors stats

list_authors: list_authors.hs
	ghc -cpp  -package QuickCheck -package util -package parsec -O -funbox-strict-fields  -Wall -Werror -i/usr/local/src/darcs-unstable -DHAVE_CURSES -optl-lcurses -optl-lz -o list_authors list_authors.hs \
		/usr/local/src/darcs-unstable/c_compat.o \
		/usr/local/src/darcs-unstable/maybe_relink.o \
		/usr/local/src/darcs-unstable/atomic_create.o \
		/usr/local/src/darcs-unstable/fpstring.o \
		/usr/local/src/darcs-unstable/umask.o \
		/usr/local/src/darcs-unstable/Autoconf.o \
		/usr/local/src/darcs-unstable/CheckFileSystem.o \
		/usr/local/src/darcs-unstable/ColourPrinter.o \
		/usr/local/src/darcs-unstable/Compat.o \
		/usr/local/src/darcs-unstable/Curl.o \
		/usr/local/src/darcs-unstable/DarcsIO.o \
		/usr/local/src/darcs-unstable/Pristine.o \
		/usr/local/src/darcs-unstable/DarcsArguments.o \
		/usr/local/src/darcs-unstable/DarcsFlags.o \
		/usr/local/src/darcs-unstable/DarcsUtils.o \
		/usr/local/src/darcs-unstable/CommandLine.o \
		/usr/local/src/darcs-unstable/DateMatcher.o \
		/usr/local/src/darcs-unstable/Depends.o \
		/usr/local/src/darcs-unstable/Diff.o \
		/usr/local/src/darcs-unstable/Exec.o \
		/usr/local/src/darcs-unstable/External.o \
		/usr/local/src/darcs-unstable/FastPackedString.o \
		/usr/local/src/darcs-unstable/FileName.o \
		/usr/local/src/darcs-unstable/FilePathMonad.o \
		/usr/local/src/darcs-unstable/FilePathUtils.o \
		/usr/local/src/darcs-unstable/IsoDate.o \
		/usr/local/src/darcs-unstable/Lcs.o \
		/usr/local/src/darcs-unstable/Lock.o \
		/usr/local/src/darcs-unstable/Map.o \
		/usr/local/src/darcs-unstable/Match.o \
		/usr/local/src/darcs-unstable/Motd.o \
		/usr/local/src/darcs-unstable/Patch.o \
		/usr/local/src/darcs-unstable/PatchApply.o \
		/usr/local/src/darcs-unstable/PatchBundle.o \
		/usr/local/src/darcs-unstable/PatchCheck.o \
		/usr/local/src/darcs-unstable/PatchChoices.o \
		/usr/local/src/darcs-unstable/PatchCommute.o \
		/usr/local/src/darcs-unstable/PatchCore.o \
		/usr/local/src/darcs-unstable/PatchInfo.o \
		/usr/local/src/darcs-unstable/PatchMatch.o \
		/usr/local/src/darcs-unstable/PatchMatchData.o \
		/usr/local/src/darcs-unstable/PatchRead.o \
		/usr/local/src/darcs-unstable/PatchReadMonads.o \
		/usr/local/src/darcs-unstable/PatchSet.o \
		/usr/local/src/darcs-unstable/PatchShow.o \
		/usr/local/src/darcs-unstable/PatchViewing.o \
		/usr/local/src/darcs-unstable/Population.o \
		/usr/local/src/darcs-unstable/PopulationData.o \
		/usr/local/src/darcs-unstable/PrintPatch.o \
		/usr/local/src/darcs-unstable/Printer.o \
		/usr/local/src/darcs-unstable/RawMode.o \
		/usr/local/src/darcs-unstable/RegChars.o \
		/usr/local/src/darcs-unstable/RepoFormat.o \
		/usr/local/src/darcs-unstable/RepoPrefs.o \
		/usr/local/src/darcs-unstable/DarcsRepo.o \
		/usr/local/src/darcs-unstable/Repository.o \
		/usr/local/src/darcs-unstable/Resolution.o \
		/usr/local/src/darcs-unstable/SHA1.o \
		/usr/local/src/darcs-unstable/SignalHandler.o \
		/usr/local/src/darcs-unstable/SlurpDirectory.o \
		/usr/local/src/darcs-unstable/Stringalike.o \
		/usr/local/src/darcs-unstable/Test.o \
		/usr/local/src/darcs-unstable/ThisVersion.o \
		/usr/local/src/darcs-unstable/UTF8.o \
		/usr/local/src/darcs-unstable/Workaround.o \
		/usr/local/src/darcs-unstable/FileSystem.o \
		/usr/local/src/darcs-unstable/AtExit.o \
		/usr/local/src/darcs-unstable/GitRepo.o \
		/usr/local/src/darcs-unstable/Add.o \
		/usr/local/src/darcs-unstable/AmendRecord.o \
		/usr/local/src/darcs-unstable/Annotate.o \
		/usr/local/src/darcs-unstable/Apply.o \
		/usr/local/src/darcs-unstable/ArgumentDefaults.o \
		/usr/local/src/darcs-unstable/Changes.o \
		/usr/local/src/darcs-unstable/Check.o \
		/usr/local/src/darcs-unstable/Context.o \
		/usr/local/src/darcs-unstable/DarcsCommands.o \
		/usr/local/src/darcs-unstable/DarcsURL.o \
		/usr/local/src/darcs-unstable/DiffCommand.o \
		/usr/local/src/darcs-unstable/Dist.o \
		/usr/local/src/darcs-unstable/Email.o \
		/usr/local/src/darcs-unstable/Get.o \
		/usr/local/src/darcs-unstable/GuiUtils.o \
		/usr/local/src/darcs-unstable/Help.o \
		/usr/local/src/darcs-unstable/Init.o \
		/usr/local/src/darcs-unstable/MainGui.o \
		/usr/local/src/darcs-unstable/Mv.o \
		/usr/local/src/darcs-unstable/Optimize.o \
		/usr/local/src/darcs-unstable/Pull.o \
		/usr/local/src/darcs-unstable/Push.o \
		/usr/local/src/darcs-unstable/Put.o \
		/usr/local/src/darcs-unstable/Query.o \
		/usr/local/src/darcs-unstable/QueryManifest.o \
		/usr/local/src/darcs-unstable/Record.o \
		/usr/local/src/darcs-unstable/RemoteApply.o \
		/usr/local/src/darcs-unstable/Remove.o \
		/usr/local/src/darcs-unstable/Repair.o \
		/usr/local/src/darcs-unstable/Replace.o \
		/usr/local/src/darcs-unstable/Resolve.o \
		/usr/local/src/darcs-unstable/Revert.o \
		/usr/local/src/darcs-unstable/Rollback.o \
		/usr/local/src/darcs-unstable/SelectChanges.o \
		/usr/local/src/darcs-unstable/Send.o \
		/usr/local/src/darcs-unstable/SetPref.o \
		/usr/local/src/darcs-unstable/Tag.o \
		/usr/local/src/darcs-unstable/TheCommands.o \
		/usr/local/src/darcs-unstable/TouchesFiles.o \
		/usr/local/src/darcs-unstable/TrackDown.o \
		/usr/local/src/darcs-unstable/Unrecord.o \
		/usr/local/src/darcs-unstable/Unrevert.o \
		/usr/local/src/darcs-unstable/WhatsNew.o

# reinstall zwiki product in plone site
# uses ~/.netrc for authorization
reinstall:
	curl -n 'http://plone.demo.zwiki.org/portal_quickinstaller/reinstallProducts?products=ZWiki'

