# Zwiki/zwiki.org makefile

# Zwiki release reminders
# -----------------------
# check for unrecorded changes
# check for translations 
# check tests pass
# check for late tracker issues
# check showAccessKeys,README,wikis/,skins/,zwiki.org HelpPage,QuickReference
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

## misc

default: test

docs: doxygen epydoc

doxygen:
	rm -rf doc/doxygen/*
	doxygen doxygen.conf

epydoc:
	rm -rf doc/epydoc/*
	epydoc --parse-only --exclude='_tests' --docformat=restructuredtext -o doc/epydoc --name=Zwiki --url=http://zwiki.org --graph=all .


## i18n

# OLD WAY - all in darcs repo. Each month:
# 1. record code changes
# 2. accept/apply any pending darcs/diff patches to po files
# 3. update pot and po files from code (make pot po) and record
#
# NEW WAY - syncing back & forth with http://launchpad.net/rosetta
# why accept changes in rosetta ? we get translations we wouldn't otherwise get
# why accept changes in darcs ? we have to sync po files with latest code
# Each month:
# 1. record code changes
# 2. accept/apply any pending darcs/diff patches to po files
# 3. download latest good po files from rosetta, msgmerge with above and record
# 4. add any new translations to makefile's language list
# 5. update pot and po files from code (make pot po) and record
# 6. re-upload all to rosetta

LANGUAGES=af ar br de en_GB es et fi fr he hu it ja nl pl pt pt_BR ro ru sv th tr zh_CN zh_TW
LANGUAGES_DISABLED=fr_CA ga

# how to set up i18nextract:
# cd /usr/local/src (or adapt ZOPE3SRC above)
# svn co svn://svn.zope.org/repos/main/Zope3/trunk Zope3
# cd Zope3; make inplace; cp sample_principals.zcml  principals.zcml
# cd ZWiki; make pot should work
# NB also add -x argument for any new directories that should be excluded
ZOPE3SRC=/usr/local/src/Zope3
I18NEXTRACT=PYTHONPATH=$(ZOPE3SRC)/src $(ZOPE3SRC)/utilities/i18nextract.py
pot:
	echo '<div i18n:domain="zwiki">' >skins/dtmlmessages.pt # dtml extraction hack
	find plugins skins wikis -name "*dtml" | xargs perl -n -e '/<dtml-translate domain="?zwiki"?>(.*?)<\/dtml-translate>/ and print "<span i18n:translate=\"\">$$1<\/span>\n";' >>skins/dtmlmessages.pt
	echo '</div>' >>skins/dtmlmessages.pt
	$(I18NEXTRACT) -d zwiki -p . -o ./i18n -x _darcs -x releases -x misc -x .NOTES -x tichu -x nautica
	tail +12 i18n/zwiki-manual.pot >>i18n/zwiki.pot
	python -c \
	   "import re; \
	    t = open('i18n/zwiki.pot').read(); \
	    t = re.sub(r'(?s)^.*?msgid',r'msgid',t); \
	    t = re.sub(r'Zope 3 Developers <zope3-dev@zope.org>',\
	               r'<zwiki@zwiki.org>', \
	               t); \
	    t = re.sub(r'(?s)(\"Generated-By:.*?\n)', \
	               r'\1\"Language-code: xx\\\n\"\n\"Language-name: X\\\n\"\n\"Preferred-encodings: utf-8 latin1\\\n\"\n\"Domain: zwiki\\\n\"\n', \
	               t); \
	    open('i18n/zwiki.pot','w').write(t)"  #one more for font-lock: "
	rm -f skins/dtmlmessages.pt

po:
	cd i18n; \
	for L in $(LANGUAGES); do \
	 msgmerge -U --no-wrap $$L.po zwiki.pot; \
	 msgmerge -U --no-wrap plone-$$L.po zwiki-plone.pot; \
	 done

# PTS auto-generates these, this is here just for sanity checking and stats
mo:
	cd i18n; \
	for L in $(LANGUAGES); do \
	 echo $$L; \
	 msgfmt --statistics $$L.po -o zwiki-$$L.mo; \
	 msgfmt --statistics plone-$$L.po -o zwiki-plone-$$L.mo; \
	 done; \
	rm -f *.mo

# tar up po files for upload to rosetta
rosettatarballs:
	cd i18n; \
	rm -f zwiki.tar zwiki-plone.tar; \
	tar cvf zwiki.tar zwiki.pot; \
	for L in $(LANGUAGES); do tar rvf zwiki.tar $$L.po; done; \
	tar cvf zwiki-plone.tar zwiki-plone.pot; \
	for L in $(LANGUAGES); do tar rvf zwiki-plone.tar plone-$$L.po; done; \
	gzip -f zwiki.tar zwiki-plone.tar; \
	mv zwiki.tar.gz zwiki-`date +%Y%m%d`.tar.gz; \
	mv zwiki-plone.tar.gz zwiki-plone-`date +%Y%m%d`.tar.gz; \



## testing

# To run Zwiki unit tests, you need Zope 2.9 or greater. Some additional
# tests will run only if Plone is installed.  

# The testrunner will test code in this INSTANCE, regardless of your
# current dir or testrunner args. Adjust the path as needed.
# For quicker testing, you may want to keep only minimal products here..
INSTANCE=/zope1

# ..and all products (eg Plone) here.
BIGINSTANCE=/zope2

# zwiki tests are kept in *_tests.py in the same directory as code
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

## upload (rsync and darcs)

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


# misc

linecounts:
	wc -l `ls *.py |grep -v _tests` |sort -nr >LINECOUNTS

PYFILES=*.py [A-Za-z]*/*.py [A-Za-z]*/*/*.py [A-Za-z]*/*/*/*.py
pyflakes:
	pyflakes $(PYFILES)

tags: xtags

etags:
	find $$PWD/ -name '*.py' -o  -name '*dtml' -o -name '*.pt' \
	  -o -name '*.css' -o -name '*.pot' -o -name '*.po' \
	  -o -name _darcs  -prune -type f \
	  -o -name contrib -prune -type f \
	  -o -name misc    -prune -type f \
	  -o -name old     -prune -type f \
	  -o -name .old     -prune -type f \
	  -o -name doc     -prune -type f \
	  -o -name .NOTES     -prune -type f \
	  | xargs etags

XTAGS=ctags-exuberant -eR --langmap=python:+.cpy.vpy,c:+.css,html:+.pt.cpt.dtml.xml.zcml 
xtags:
	$(XTAGS) --exclude=@.tagsexclude * || $(XTAGS) *

zopetags:
	cd /zope/lib/python; \
	  ~/bin/eptags.py `find $$PWD/ -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

getproducts:
	cd /zope2/Products; \
	  rsync -rl --progress --exclude="*.pyc" zwiki.org:/zope2/Products . 

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

clean:
	rm -f .*~ *~ *.tgz *.bak *.hi *.ho `find . -name "*.pyc"`

Clean: clean
	rm -f i18n/*.mo skins/dtmlmessages.pt


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

# ensure all files in zwiki.org repo have the right permissions for all
# users, darcs mail-in etc. Everything should have group "zwiki", be
# group-writable, and directories should have the setgid bit set.
# May need to run this periodically since certain operations mess up
# the permissions, such as... (?)
# Run this as root in the ZWiki dir on zwiki.org.

fixperms:
	chgrp -R zwiki *
	chmod -R ug+rw *
	find . -type d -exec chmod g+s {}  \; 
