# Zwiki/zwiki.org makefile

# Zwiki release reminders
# -----------------------
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

LANGUAGES=af ar de en_GB es et fi fr he hu it ja nl pl pt pt_BR ro ru sv th tr zh_CN zh_TW
LANGUAGES_DISABLED=fr_CA ga
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
	 msgmerge -U $$L.po zwiki.pot; \
	 msgmerge -U plone-$$L.po zwiki-plone.pot; \
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
# tests will run if you have CMF, Plone, PlacelessTranslationService.
# For quicker testing, you may want to use a zope instance with minimal
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
