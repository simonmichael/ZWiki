# Zwiki/zwiki.org makefile

# simple no-branch release process
# --------------------------------
# check for unrecorded changes
# check tests pass
# check for late tracker issues
# check showAccessKeys,README,wikis/,skins/,zwiki.org HelpPage,QuickReference
# update CHANGES.txt from darcs changes --from-tag=0.xx
# update version.txt
# make Release
# update KnownIssues,OldKnownIssues,#zwiki
# mail announcement to zwiki@zwiki.org, zope-announce@zope.org

PRODUCT=ZWiki
HOST=zwiki.org
REPO=$(HOST):/repos/$(PRODUCT)
RSYNCPATH=$(HOST):/repos/$(PRODUCT)
LHOST=localhost:8080
CURL=curl -o.curllog -sS -n

## misc

default: test

epydoc:
	PYTHONPATH=/zope/lib/python \
	 epydoc --docformat restructuredtext \
	        --output /var/www/zopewiki.org/epydoc  \
	        /zope/lib/python/Products/* /zope2/Products/*

epydoc2:
	PYTHONPATH=. \
	cd /zope/lib/python; \
	epydoc \
	-o /var/www/zopewiki.org/epydoc \
	-n Zope-2.7.1b2 \
	AccessControl/ App BDBStorage/ DateTime/ DBTab/ DocumentTemplate/ HelpSys/ OFS/ Persistence/ SearchIndex/ Shared/ Signals/ StructuredText/ TAL/ webdav/ ZClasses/ ZConfig/ zExceptions/ zLOG/ Zope ZopeUndo/ ZPublisher/ ZServer/ ZTUtils/ PageTemplates ExternalMethod Mailhost MIMETools OFSP PluginIndexes PythonScripts Sessions SiteAccess SiteErrorLog




## i18n

# OLD WAY - all in darcs repo. Each month:
# 1. record code changes
# 2. accept/apply any pending darcs/diff patches to po files
# 3. update pot and po files from code (make pot po) and record
#
# NEW WAY - syncing back & forth with http://launchpad.net/rosetta
# why update in rosetta ? we get translations we wouldn't otherwise get
# why update in repo ? we have to update from the latest code there
# Each month:
# 1. record code changes
# 2. accept/apply any pending darcs/diff patches to po files
# 3. download latest good po files from rosetta, merge with above and record
# 4. add any new translations to makefile's language list
# 5. update pot and po files from code (make pot po) and record
# 6. re-upload all to rosetta

LANGUAGES=af ar de en-GB es et fi fr he hu it ja nl pl pt pt-BR ro ru sv tr zh-CN zh-TW 
LANGUAGES_DISABLED=fr-CA ga

I18NEXTRACT=/zope3/bin/i18nextract # still need to patch this, see zopewiki

pot:
	echo '<div i18n:domain="zwiki">' >skins/dtmlmessages.pt # dtml extraction hack
	find plugins skins wikis -name "*dtml" | xargs perl -n -e '/<dtml-translate domain="?zwiki"?>(.*?)<\/dtml-translate>/ and print "<span i18n:translate=\"\">$$1<\/span>\n";' >>skins/dtmlmessages.pt
	echo '</div>' >>skins/dtmlmessages.pt

	$(I18NEXTRACT) -d zwiki -p . -o ./i18n \
	    -x _darcs -x .old -x misc -x ftests  -x .doxygen
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
	 msgmerge -U zwiki-$$L.po zwiki.pot; \
	 msgmerge -U zwiki-plone-$$L.po zwiki-plone.pot; \
	 done

# PTS auto-generates these, this is here just for sanity checking and stats
mo:
	cd i18n; \
	for L in $(LANGUAGES); do \
	 echo $$L; \
	 msgfmt --statistics zwiki-$$L.po -o zwiki-$$L.mo; \
	 msgfmt --statistics zwiki-plone-$$L.po -o zwiki-plone-$$L.mo; \
	 done; \
	rm -f *.mo

potarball:
	cd i18n; \
	tar cvf zwiki.tar zwiki.pot; \
	for L in $(LANGUAGES); do tar rvf zwiki.tar zwiki-$$L.po; done; \
	tar cvf zwiki-plone.tar zwiki-plone.pot; \
	for L in $(LANGUAGES); do tar rvf zwiki-plone.tar zwiki-plone-$$L.po; done; \
	gzip -f zwiki.tar zwiki-plone.tar



## testing

# to run Zwiki unit tests, you probably need:
# Zope 2.7.3 or greater
# ZopeTestCase, linked under .../lib/python/Testing
# CMF 1.5
# Plone 
# PlacelessTranslationService ? maybe

# all tests, test.py
# avoid mailin tests hanging due to #1104
WHICH_TESTS=''

# for quicker testing, you may want to use a zope instance with minimal
# products installed. Also note the testrunner will run code from
# zopectl's INSTANCE_HOME, regardless of your current dir or testrunner
# args.
QUICKZOPE=/zope1/bin/zopectl
FULLZOPE=/zope2/bin/zopectl
TESTARGS=test --tests-pattern='_tests$$' --test-file-pattern='_tests$$' -m Products.ZWiki
QUICKTEST=$(QUICKZOPE) $(TESTARGS)
FULLTEST=$(FULLZOPE) $(TESTARGS) -a 3

test:
	$(QUICKTEST) -q

testv:
	$(QUICKTEST) -v

testvv:
	$(QUICKTEST) -vv

testall:
	$(FULLTEST) -vv

# silliness to properly capture output of a test run
testresults:
	date >.testresults 
	make -s test >>.testresults 2>.stderr
	cat .stderr >>.testresults
	rm -f .stderr

## upload (rsync and darcs)

rcheck:
	rsync -ruvC -e ssh -n . $(RSYNCPATH)

rpush:
	rsync -ruvC -e ssh . $(RSYNCPATH)

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

Release: releasenotes version releasetag tarball push rpush

# record CHANGES.txt.. 
releasenotes:
	@echo recording release notes
	@darcs record -am 'update release notes' CHANGES.txt

# bump version number in various places and record; don't have other
# changes in these files
version:
	@echo bumping version to $(VERSIONNO)
	@(echo 'Zwiki' $(VERSIONNO) `date +%Y/%m/%d`; echo)|cat - CHANGES.txt \
	  >.temp; mv .temp CHANGES.txt
	@perl -pi -e "s/__version__='.*?'/__version__='$(VERSIONNO)'/" \
	  __init__.py
	@perl -pi -e "s/Zwiki version [0-9a-z.-]+/Zwiki version $(VERSIONNO)/"\
	  wikis/basic/HelpPage.stx
	@darcs record -am 'bump version to $(VERSIONNO)' \
	  version.txt CHANGES.txt __init__.py wikis/basic/HelpPage.stx

releasetag:
	@echo tagging release-$(VERSION)
	@darcs tag --checkpoint -m release-$(VERSION) 

# always puts tarball in mainbranch/releases
# look at darcs dist
tarball: clean
	@echo building $(FILE) tarball
	@cp -r _darcs/current $(PRODUCT)
	@tar -czvf releases/$(FILE) --exclude Makefile $(PRODUCT)
	@rm -rf $(PRODUCT)


# misc

tags:
	find $$PWD/ -name '*.py' -o  -name '*dtml' -o -name '*.pt' \
	  -o -name '*.css' -o -name '*.pot' -o -name '*.po' \
	  -o -name _darcs  -prune -type f \
	  -o -name contrib -prune -type f \
	  -o -name misc    -prune -type f \
	  -o -name old     -prune -type f \
	  -o -name .old     -prune -type f \
	  -o -name doxygen -prune -type f \
	  -o -name .doxygen -prune -type f \
	  | xargs etags --language-force=python #make sure non-py files are included

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
	rm -f .*~ *~ *.tgz *.bak `find . -name "*.pyc"`

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

#fixissuepermissions:
#	for ISSUE in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010; do \
#	  echo "$(HOST): fixing permissions for IssueNo$$ISSUE" ;\
#	  $(CURL) "http://$(HOST)/IssueNo$$ISSUE/manage_permission?permission_to_manage=Change+ZWiki+Page+Types" ;\
#	done
#
#fixcreationtimes:
#	for ISSUE in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010\
#	  0011 0012 0013 0014 0015 0016 0017 0018 0019 0020\
#	  0021 0022 0023 0024 0025 0026 0027 0028 0029 0030\
#	  0031 0032 0033 0034 0035 0036 0037 0038 0039 0040\
#	  0041 0042 0043 0044 0045 0046 0047 0048 0049 0050\
#	  0051 0052 0053 0054; do \
#	  echo "$(HOST): fixing creation time for IssueNo$$ISSUE" ;\
#	  $(CURL) "http://$(HOST)/IssueNo$$ISSUE/manage_changeProperties?creation_time=2001/11/26+18%3A09+PST" ;\
#	done
#
#updatecatalog:
#	@echo updating Catalog on $(HOST)
#	@$(CURL) "http://$(HOST)/Catalog/manage_catalogReindex"
