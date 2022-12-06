# Zwiki/zwiki.org makefile

# Zwiki release checklist
# -----------------------
# check for unrecorded changes
# check for translations
# check tests pass
# check for late tracker issues
# check README,content/,skins/,zwiki.org HelpPage,QuickReference
# darcs changes --from-tag NN into CHANGES.txt & edit; don't add header at top
# update version.txt, don't record
# make release
# restart joyful.com/zwiki.org server, smoke test
# announce
#  check FrontPage, KnownIssues
#  #zwiki, zwiki@zwiki.org (rc)
#  #zwiki, zwiki@zwiki.org, zope-announce@zope.org, python list ? (final)

PRODUCT=ZWiki
HOST=zwiki.org
REPO=$(HOST):/repos/$(PRODUCT)
RSYNCPATH=$(HOST):/repos/$(PRODUCT)
LHOST=localhost:8080
CURL=curl -o.curllog -sS -n


default: test


## docs

doc: sphinx

sphinx:
	make -f .sphinx.mk html

doxygen:
	rm -rf doc/doxygen/*
	doxygen .doxygen.conf

epydoc:
	rm -rf doc/epydoc/*
	epydoc --parse-only --exclude='_tests' --docformat=restructuredtext -o doc/epydoc --name=Zwiki --url=http://zwiki.org --graph=all .



## i18n

# translation update checklist
# ----------------------------
# *translators* update translations through launchpad, any time
# *developers* update and upload pot files, any time
# *release manager*, before release:
#  1. update pot file and upload to launchpad
#   make pot, record
#   https://translations.launchpad.net/zwiki/trunk/+pots/zwiki/+upload
#   wait for upload (https://translations.launchpad.net/zwiki/trunk/+imports)
#  2. download latest translations from launchpad
#   https://translations.launchpad.net/zwiki/trunk/+pots/zwiki/+export (everything, partial po format)
#   https://translations.launchpad.net/zwiki/trunk/+pots/zwiki-plone/+export
#   wait for mail, unpack download links into i18n/ :
#    cd i18n
#    curl http://launchpadlibrarian.net/NNNNNNNN/launchpad-export.tar.gz | tar xzvf - --strip-components=1
#    curl http://launchpadlibrarian.net/NNNNNNNN/launchpad-export.tar.gz | tar xzvf - --strip-components=1
#   check for new languages: darcs wh -sl i18n
#   make po, record
#  3. re-upload po files to update status bars
#   make poupload
#   https://translations.launchpad.net/zwiki/trunk/+pots/zwiki/+upload
#   wait for upload (https://translations.launchpad.net/zwiki/trunk/+imports)
#
# problems:
#  launchpad strips out some #. Default lines ? need them ?
#  zwiki-plone.pot complicates, figure out how to simplify

LANGUAGES=af ar de en_GB es et fi fr he hu it ja nl pl pt pt_BR ro ru sv th tr zh_CN zh_TW #fr_CA ga

# requires 18ndude >= 2008/02/06
pot:
	echo '<div i18n:domain="zwiki">' >skins/dtmlmessages.pt # dtml extraction hack
	find plugins skins content -name "*dtml" | xargs perl -n -e '/<dtml-translate domain="?zwiki"?>(.*?)<\/dtml-translate>/ and print "<span i18n:translate=\"\">$$1<\/span>\n";' >>skins/dtmlmessages.pt                           #
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
# We provide some handy make rules to help run Zwiki unit & functional tests.
# Prerequisites:
# - install at least Zope 2.10
# - install or symlink your ZWiki directory in $INSTANCE/Products
# - if necessary (eg if you symlink) adjust INSTANCE paths below
# Examples:
#   make test                            # run most tests quickly
#   make testall                         # run all tests verbosely
#   make test_methodregexp               # run one or more matching tests
#   make testmod_Modulename              # run all tests for a module
#   make testmod_"pagetypes.rst -D"      # run rst tests and debug any failure
#   make testmod_Functional              # run only functional tests
#   make testresults                     # log "make testall" output in TESTRESULTS
#   make testrunnerhelp                  # see testrunner arguments reference

# To run Zwiki unit tests: install Zope 2.10, adjust INSTANCE paths,
# install or link your ZWiki directory in $INSTANCE/Products.
# Some additional tests will run if Plone is installed.
# minimal products, fast startup
INSTANCE=/zope1
# all products
BIGINSTANCE=/zope2

# zwiki's tests are in *_tests.py files, found in tests/ and other places
ZWIKITESTS=--tests-pattern='_tests$$'

# run tests as quickly as possible
TEST=$(INSTANCE)/bin/zopectl test $(ZWIKITESTS) --keepbytecode -v #--nowarnings
TESTV=$(TEST) -v

# run all tests verbosely and thoroughly
TESTALL=$(BIGINSTANCE)/bin/zopectl test $(ZWIKITESTS) -a 3 -vv

test:
	$(TEST) -m Products.ZWiki

testv:
	$(TESTV) -m Products.ZWiki

testall:
	$(TESTALL) -m Products.ZWiki

test_%:
	$(TEST) -m Products.ZWiki -t $*

testmod_%:
	$(TEST) -m Products.ZWiki.$*

TESTRESULTS=TESTRESULTS
.PHONY: testresults
testresults:
	@rm -f $(TESTRESULTS)
	@date >$(TESTRESULTS)
	@make -s test >>$(TESTRESULTS) 2>.stderr
	@cat .stderr >>$(TESTRESULTS)
	@rm -f .stderr

testrunnerhelp:
	$(INSTANCE)/bin/zopectl test --help



## release

VERSION:=$(shell cut -c7- version.txt )
MAJORVERSION:=$(shell echo $(VERSION) | sed -e's/-[^-]*$$//')
VERSIONNO:=$(shell echo $(VERSION) | sed -e's/-/./g')
FILE:=$(PRODUCT)-$(VERSIONNO).tgz

release: releasenotes version releasetag tarball push rpush

releasenotes:
	@echo recording release notes
	@darcs record -am 'release notes' CHANGES.txt

# bump version number in various places and record; don't have other
# changes in these files
version:
	@echo bumping version to $(VERSIONNO)
	@(echo 'Zwiki' $(VERSIONNO) `date +%Y/%m/%d`; echo '======================='; echo)|cat - CHANGES.txt \
	  >.temp; mv .temp CHANGES.txt
	@perl -pi -e "s/__version__='.*?'/__version__='$(VERSIONNO)'/" \
	  __init__.py
	@perl -pi -e "s/Zwiki version [0-9a-z.-]+/Zwiki version $(VERSIONNO)/"\
	  skins/zwiki/HelpPage.stx
	@darcs record -am 'bump version to $(VERSIONNO)' \
	  version.txt CHANGES.txt __init__.py skins/zwiki/HelpPage.stx

releasetag:
	@echo tagging release-$(VERSION)
	darcs tag release-$(VERSION)

# save a release tarball in releases
tarball: clean
	@echo building $(FILE) tarball
	darcs dist --tag release-$(VERSION) --dist-name $(PRODUCT)
	mv $(PRODUCT).tar.gz releases/$(PRODUCT)-$(VERSIONNO).tgz



## misc. syncing

rcheck:
	rsync -ruvC -e ssh -n releases $(RSYNCPATH)

rpush:
	rsync -ruvC -e ssh releases $(RSYNCPATH)

check:
	darcs whatsnew --summary

push:
	darcs push -v -a $(REPO)



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
	rm -f `find . -name '.*~' -o -name '*~' -o -name '*.bak' -o -name '*-darcs-backup*'`

Clean: clean
	rm -f i18n/*.mo skins/dtmlmessages.pt
	rm -f `find . -name '*.pyc'`

# ensure all files in zwiki.org repo have the right permissions for all
# users, darcs mail-in etc. Everything should have group "zwiki", be
# group-writable, and directories should have the setgid bit set.
# May need to run this periodically since certain operations mess up
# the permissions, such as... (?)
# Run as superuser in the ZWiki dir on zwiki.org.
fixperms:
	chgrp -R zwiki .
	chmod -R ug+rw .
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

# reinstall zwiki product in plone site
# uses ~/.netrc for authorization
reinstall:
	curl -n 'http://plone.demo.zwiki.org/portal_quickinstaller/reinstallProducts?products=ZWiki'

# generate code summary
summarize:
	tools/summarize

#summarypdf:
#	aquamacs SUMMARY, print, save as SUMMARY.pdf

summaryhtml:
	pdftohtml -c -noframes SUMMARY.pdf SUMMARY.html
