# Zwiki/zwiki.org makefile

# simple no-branch release process
# --------------------------------
# check for unrecorded changes
# check tests pass
# check for late tracker issues
# check showAccessKeys,README,content/,skins/,zwiki.org HelpPage,QuickReference
# update CHANGES.txt from darcs changes
# update version.txt
# make Release
# update FrontPage,KnownIssues,OldKnownIssues,ReleaseNotes,discussion,#zwiki
# final: mail to zwiki@zwiki.org, zope(-announce)@zope.org

PRODUCT=ZWiki
HOST=zwiki.org
REPO=$(HOST):/usr/local/src/$(PRODUCT)
RSYNCPATH=$(HOST):/usr/local/src/$(PRODUCT)
LHOST=localhost:8080
CURL=curl -o.curllog -sS -n

## misc

default: test

# regenerate dtml-based templates
CLEAN=perl -p -e "s/(?s)^\#parents:.*?\n//;"
dtml:
	@echo regenerating dtml-based skin templates from pages
	$(CLEAN) content/dtml/RecentChanges.stxdtml \
	  >skins/standard/recentchangesdtml.dtml
	$(CLEAN) content/dtml/SearchPage.stxdtml \
	  >skins/standard/searchwikidtml.dtml
	$(CLEAN) content/dtml/UserOptions.stxdtml \
	  >skins/standard/useroptionsdtml.dtml
	$(CLEAN) content/tracker/IssueTracker.stxdtml \
	  >skins/standard/issuetrackerdtml.dtml
	$(CLEAN) content/tracker/FilterIssues.stxdtml \
	  >skins/standard/filterissuesdtml.dtml
	cp skins/standard/{recentchanges,searchwiki,useroptions,issuetracker,filterissues}dtml.dtml skins/zwiki_plone

epydoc:
	PYTHONPATH=/zope/lib/python \
	 epydoc --docformat restructuredtext \
	        --output /var/www/zopewiki.org/epydoc  \
	        /zope/lib/python/Products/* /zope1/Products/*

epydoc2:
	PYTHONPATH=. \
	cd /zope/lib/python; \
	epydoc \
	-o /var/www/zopewiki.org/epydoc \
	-n Zope-2.7.1b2 \
	AccessControl/ App BDBStorage/ DateTime/ DBTab/ DocumentTemplate/ HelpSys/ OFS/ Persistence/ SearchIndex/ Shared/ Signals/ StructuredText/ TAL/ webdav/ ZClasses/ ZConfig/ zExceptions/ zLOG/ Zope ZopeUndo/ ZPublisher/ ZServer/ ZTUtils/ PageTemplates ExternalMethod Mailhost MIMETools OFSP PluginIndexes PythonScripts Sessions SiteAccess SiteErrorLog


## i18n
# remember: 1. merge source files 2. make pot 3. replace po files 4. make po
# using zope 3's i18nextract.py with zopewiki/ZopeInternationalization patches

LANGUAGES=en es fr-CA fr ga it zh-TW pt-BR zh-CN pl nl
ZOPE3SRC=/usr/local/src/Zope3/src
EXTRACT=PYTHONPATH=$(ZOPE3SRC) python /usr/local/src/Zope3/utilities/i18nextract.py

pot: dtmlextract
	$(EXTRACT) -d zwiki -p . -o ./i18n \
	    -x _darcs -x old -x misc -x ftests 
	tail +12 i18n/zwiki-manual.pot >>i18n/zwiki.pot
	python \
	-c "import re; \
	    t = open('i18n/zwiki.pot').read(); \
	    t = re.sub(r'(?s)^.*?msgid',r'msgid',t); \
	    t = re.sub(r'Zope 3 Developers <zope3-dev@zope.org>',\
	               r'<zwiki@zwiki.org>', \
	               t); \
	    t = re.sub(r'(?s)(\"Generated-By:.*?\n)', \
	               r'\1\"Language-code: xx\\\n\"\n\"Language-name: X\\\n\"\n\"Preferred-encodings: utf-8 latin1\\\n\"\n\"Domain: zwiki\\\n\"\n', \
	               t); \
	    open('i18n/zwiki.pot','w').write(t)"

# a dtml extraction hack, should integrate with i18nextract
dtmlextract: 
	echo '<div i18n:domain="zwiki">' >skins/dtmlmessages.pt
	find skins content -name "*dtml" | xargs perl -n -e '/<dtml-translate domain="?zwiki"?>(.*?)<\/dtml-translate>/ and print "<span i18n:translate=\"\">$$1<\/span>\n";' >>skins/dtmlmessages.pt
	echo '</div>' >>skins/dtmlmessages.pt

po:
	cd i18n; \
	for L in $(LANGUAGES); do \
	 msgmerge -U zwiki-$$L.po zwiki.pot; \
	 msgmerge -U zwiki-plone-$$L.po zwiki-plone.pot; \
	 done

mo:
	cd i18n; \
	for L in $(LANGUAGES); do \
	 echo $$L; \
	 msgfmt --statistics zwiki-$$L.po -o zwiki-$$L.mo; \
	 msgfmt --statistics zwiki-plone-$$L.po -o zwiki-plone-$$L.mo; \
	 done

## testing

# all tests, test.py
test:
	PYTHONPATH=/zope/lib/python SOFTWARE_HOME=/zope/lib/python INSTANCE_HOME=/zope1 \
	  python /zope/test.py --libdir .

# all tests, gui
gtest:
	PYTHONPATH=/zope/lib/python SOFTWARE_HOME=/zope/lib/python INSTANCE_HOME=/zope1 \
	  python /zope/test.py -m --libdir .

# a single test module
test%:
	PYTHONPATH=/zope/lib/python SOFTWARE_HOME=/zope/lib/python INSTANCE_HOME=/zope1 \
	  python tests/test$*.py

# test with argument(s)
#test%:
#	export PYTHONPATH=/zope/lib/python:/zope1; \
#	  python test.py -v --libdir $$PWD/tests $*

#XXX currently broken
rtest:
	ssh $(HOST) 'cd zwiki; make test'

rtest%:
	ssh $(HOST) "cd zwiki; make rtest$*"

#ftest:
#	ssh zwiki.org /usr/local/zope/instance/Products/ZWiki/functionaltests/run_tests -v zwiki


## upload (rsync and darcs)

rcheck:
	rsync -ruvC -e ssh -n . $(RSYNCPATH)

rpush:
	rsync -ruvC -e ssh . $(RSYNCPATH)

check: 
	darcs whatsnew --summary

push:
	darcs push -v -a $(REPO)

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
	  content/basic/HelpPage.stx
	@darcs record -am 'bump version to $(VERSIONNO)' \
	  version.txt CHANGES.txt __init__.py content/basic/HelpPage.stx

releasetag:
	@echo tagging release-$(VERSION)
	@darcs tag -m release-$(VERSION) \
	  `echo $(VERSION)|perl -ne '!/rc/ and print "--checkpoint"'`

# always puts tarball in mainbranch/releases
# look at darcs dist
tarball: clean
	@echo building $(FILE) tarball
	@cp -r _darcs/current $(PRODUCT)
	@tar -czvf $(HOME)/zwiki/releases/$(FILE) --exclude Makefile $(PRODUCT)
	@rm -rf $(PRODUCT)


# misc

tags:
	find $$PWD/ -name '*.py' -o  -name '*dtml' -o -name '*.pt' \
	  -o -name '*.pot' -o -name '*.po' \
	  -o -name _darcs  -prune -type f \
	  -o -name contrib -prune -type f \
	  -o -name misc    -prune -type f \
	  -o -name old     -prune -type f \
	  | xargs etags

zopetags:
	cd /zope/lib/python; \
	  ~/bin/eptags.py `find $$PWD -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

producttags:
	cd /var/lib/zope/Products; \
	  ~/bin/eptags.py `find $$PWD -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

alltags: tags producttags zopetags
	cat TAGS /zope1/Products/TAGS /zope/lib/python/TAGS \
	 >TAGS.all

plonetags:
	cd /zope1/Products/CMFPlone; \
	  ~/bin/eptags.py \
	  `find $$PWD -name '*.py' -o -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

clean:
	rm -f .*~ *~ *.tgz *.bak 

Clean: clean
	rm -f i18n/*.mo skins/dtmlmessages.pt


## old stuff

# server control

revert: 
	@echo reverting $(HOST) $(PRODUCT) to standard darcs version
	@ssh $(HOST) 'cd zwiki;darcs revert -a'

restart:
	@echo restarting zope on $(HOST)
	ssh $(HOST) 'zopectl restart'

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

# misc automation

#cvschangelog:
#	cvs2cl --follow trunk --day-of-week
#	cvs commit -m 'latest' ChangeLog

#analyzezodb:
#	ssh zwiki.org 'export ZOPEVERSION=2.6.1; export ZOPEHOME=/usr/local/zope/$$ZOPEVERSION; export INSTANCE_HOME=/usr/local/zope/instance; export SOFTWARE_HOME=$$ZOPEHOME/lib/python; export PYTHONPATH=$$SOFTWARE_HOME:$$ZOPEHOME:$$INSTANCE_HOME; /usr/local/bin/ZODBAnalyze.py ~simon/var/Data.fs >~simon/ZWiki/zodb_report.txt'

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
#
#clearcatalog:
#	@echo clearing Catalog on $(HOST)
#	@$(CURL) "http://$(HOST)/Catalog/manage_catalogClear"

# zope.org upkeep

PRODUCTURL=http://zope.org/Members/simon/Zwiki
PLATFORM=All
MATURITY=Development
LICENSE=GPL
INFOURL=http://zwiki.org
CHANGESURL=http://zwiki.org/ReleaseNotes
LICENSEURL=http://zwiki.org/ZwikiLicense
INSTALLATIONURL=http://zwiki.org/InstallationGuide
LANGUAGE=en
#SUBJECTS="Collector,Community,Content Object,DTML,Editors,Educational,Email,ExternalEditor,FTP,Files,HTML,Images,Open Source,Page Templates,Software,Structured Text,Zope Product"
# have to do it this way for curl to my knowledge
SUBJECTS=\
 -Fpredefined_subjects:list="Collector" \
 -Fpredefined_subjects:list="Community" \
 -Fpredefined_subjects:list="Content Object" \
 -Fpredefined_subjects:list="DTML" \
 -Fpredefined_subjects:list="Editors" \
 -Fpredefined_subjects:list="Educational" \
 -Fpredefined_subjects:list="Email" \
 -Fpredefined_subjects:list="ExternalEditor" \
 -Fpredefined_subjects:list="FTP" \
 -Fpredefined_subjects:list="Files" \
 -Fpredefined_subjects:list="HTML" \
 -Fpredefined_subjects:list="Images" \
 -Fpredefined_subjects:list="Open Source" \
 -Fpredefined_subjects:list="Page Templates" \
 -Fpredefined_subjects:list="Software" \
 -Fpredefined_subjects:list="Structured Text" \
 -Fpredefined_subjects:list="Zope Product"
NEWSITEM=$(PRODUCT)-$(VERSION)-released

zdo-release: zdo-swrelease zdo-swreleasefile

#zdo-newsitem: 

zdo-swrelease: zdo-swrelease-create zdo-swrelease-edit \
	zdo-swrelease-metadata zdo-swrelease-publish

zdo-swreleasefile: zdo-swreleasefile-create zdo-swreleasefile-edit \
	zdo-swreleasefile-metadata zdo-swreleasefile-publish

#zdo-swpackage-create:
#	@echo creating the $(PRODUCT) Software Package on zope.org
#	@curl -nsS \
#	 -Fid=$(VERSIONNO)
#	 -Ftitle=''
#	 -Ffile=@$(HOME)/zwiki/releases/$(FILE)
#	 $(PRODUCTURL)/manage_addProduct/ZopeSite/Release_factory/Release_add

zdo-swpackage-update-latest-release-warning:
	make zdo-swpackage-retract
	@echo updating the current release link on zope.org
	@echo edit at $(PRODUCTURL)/swpackage_edit_form
#	curl -nsS \
#	 -Fname=$(VERSIONNO) \
#	 -Fversion=$(VERSIONNO) \
#	 -Fmaturity=$(MATURITY) \
#	 -Flicense=$(LICENSE) \
#	 -Finfo_url=$(INFOURL) \
#	 -Fchanges_url=$(CHANGESURL) \
#	 -Flicense_url=$(LICENSEURL) \
#	 -Finstallation_url=$(INSTALLATIONURL) \
#	 $(PRODUCTURL)/swpackage_edit
	make zdo-swpackage-publish

#zdo-swpackage-edit:
#	@echo configuring the $(PRODUCT) Software Package on zope.org
#	curl -nsS \
#	 -Fname=$(VERSIONNO) \
#	 -Fversion=$(VERSIONNO) \
#	 -Fmaturity=$(MATURITY) \
#	 -Flicense=$(LICENSE) \
#	 -Finfo_url=$(INFOURL) \
#	 -Fchanges_url=$(CHANGESURL) \
#	 -Flicense_url=$(LICENSEURL) \
#	 -Finstallation_url=$(INSTALLATIONURL) \
#	 $(PRODUCTURL)/swpackage_edit
#	@echo

zdo-swpackage-publish:
	@echo publishing the $(PRODUCT) Software Package on zope.org
	curl -nsS \
	 -Feffective_date= \
	 -Fexpiration_date= \
	 -Fcomment= \
	 -Fworkflow_action=submit \
	 -Fworkflow_action_submit=Save \
	 -Fform_submitted=content_status_history \
	 $(PRODUCTURL)/portal_form/content_status_history
	@echo

zdo-swpackage-retract:
	@echo retracting the $(PRODUCT) Software Package on zope.org
	curl -nsS \
	 -Feffective_date= \
	 -Fexpiration_date= \
	 -Fcomment= \
	 -Fworkflow_action=retract \
	 -Fworkflow_action_submit=Save \
	 -Fform_submitted=content_status_history \
	 $(PRODUCTURL)/portal_form/content_status_history
	@echo

zdo-swrelease-create:
	@echo creating the $(VERSIONNO) Software Release on zope.org
	@curl -nsS \
	 -Fid=$(VERSIONNO) \
	 -Ftype_name='Software Release' \
	 $(PRODUCTURL)/createObject
	@echo

zdo-swrelease-edit:
	@echo configuring the $(VERSIONNO) Software Release on zope.org
	curl -nsS \
	 -Fname=$(VERSIONNO) \
	 -Fversion=$(VERSIONNO) \
	 -Fmaturity=$(MATURITY) \
	 -Flicense=$(LICENSE) \
	 -Finfo_url=$(INFOURL) \
	 -Fchanges_url=$(CHANGESURL) \
	 -Flicense_url=$(LICENSEURL) \
	 -Finstallation_url=$(INSTALLATIONURL) \
	 $(PRODUCTURL)/$(VERSIONNO)/swrelease_edit
	@echo

zdo-swrelease-metadata:
	@echo configuring metadata for the $(VERSIONNO) Software Release on zope.org
	curl -nsS \
	 -FallowDiscussion=default \
	 $(SUBJECTS) \
	 -Feffective_date= \
	 -Fexpiration_date= \
	 -Fformat=application/x-gtar \
	 -Flanguage=$(LANGUAGE) \
	 -Frights= \
	 -Fcontributors:lines= \
	 $(PRODUCTURL)/$(VERSIONNO)/metadata_edit
	@echo

zdo-swrelease-publish:
	@echo publishing the $(VERSIONNO) Software Release on zope.org
	curl -nsS \
	 -Feffective_date= \
	 -Fexpiration_date= \
	 -Fcomment= \
	 -Fworkflow_action=submit \
	 -Fworkflow_action_submit=Save \
	 -Fform_submitted=content_status_history \
	 $(PRODUCTURL)/$(VERSIONNO)/portal_form/content_status_history
	@echo

zdo-swrelease-retract:
	@echo retracting the $(VERSIONNO) Software Release on zope.org
	curl -nsS \
	 -Feffective_date= \
	 -Fexpiration_date= \
	 -Fcomment= \
	 -Fworkflow_action=retract \
	 -Fworkflow_action_submit=Save \
	 -Fform_submitted=content_status_history \
	 $(PRODUCTURL)/$(VERSIONNO)/portal_form/content_status_history
	@echo

zdo-swreleasefile-create:
	@echo creating the $(FILE) Software Release File on zope.org
	@curl -nsS \
	 -Fid=$(FILE) \
	 -Ftype_name='Software Release File' \
	 $(PRODUCTURL)/$(VERSIONNO)/createObject
	@echo

zdo-swreleasefile-edit:
	@echo uploading to the $(FILE) Software Release File on zope.org
	curl -nsS \
	 -Ffilename=$(FILE) \
	 -Fplatform=$(PLATFORM) \
	 -Ffile=@$(HOME)/zwiki/releases/$(FILE) \
	 $(PRODUCTURL)/$(VERSIONNO)/$(FILE)/swreleasefile_edit
	@echo

# NB - need to set content_type in manage_propertiesForm manually, zdo bug
zdo-swreleasefile-metadata:
	@echo configuring metadata for the $(FILE) Software Release File on zope.org
	curl -nsS \
	 -Fname=$(VERSIONNO) \
	 -FallowDiscussion=default \
	 $(SUBJECTS) \
	 -Feffective_date= \
	 -Fexpiration_date= \
	 -Fformat=application/x-gtar \
	 -Flanguage=$(LANGUAGE) \
	 -Frights= \
	 -Fcontributors:lines= \
	 $(PRODUCTURL)/$(VERSIONNO)/$(FILE)/metadata_edit
	@echo

zdo-swreleasefile-publish:
	@echo publishing the $(FILE) Software Release File on zope.org
	curl -nsS \
	 -Feffective_date= \
	 -Fexpiration_date= \
	 -Fcomment= \
	 -Fworkflow_action=submit \
	 -Fworkflow_action_submit=Save \
	 -Fform_submitted=content_status_history \
	 $(PRODUCTURL)/$(VERSIONNO)/$(FILE)/portal_form/content_status_history
	@echo

zdo-swreleasefile-retract:
	@echo retracting the $(FILE) Software Release File on zope.org
	curl -nsS \
	 -Feffective_date= \
	 -Fexpiration_date= \
	 -Fcomment= \
	 -Fworkflow_action=retract \
	 -Fworkflow_action_submit=Save \
	 -Fform_submitted=content_status_history \
	 $(PRODUCTURL)/$(VERSIONNO)/$(FILE)/portal_form/content_status_history
	@echo

#zdo-newsitem-create:
#	@echo creating the $(VERSIONNO) News Item on zope.org
#	@curl -nsS \
#	 -Fid=$(VERSIONNO)
#	 -Ftitle=''
#	 -Ffile=@$(HOME)/zwiki/releases/$(FILE)
#	 $(PRODUCTURL)/manage_addProduct/ZopeSite/Release_factory/Release_add
#
#zdoannounce-create:
#	@echo creating $(NEWSITEM) news item on zope.org
#	@curl -nsSo.curllog -Fid=$(NEWSITEM) -Ftitle="" -Ftext="" -F"submit= Add " $(PRODUCTURL)/manage_addProduct/ZopeSite/fNewsItem/addNewsItem
#
#zdo-newsitem-configure:
#	@echo configuring the $(VERSIONNO) News Item on zope.org
#	curl -nsSo.curllog \
#	 -Fname=$(VERSIONNO) \
#	 -Finfo_url=$(INFOURL) \
#	 -Fchanges_url=$(CHANGESURL) \
#	 -Flicense_url=$(LICENSEURL) \
#	 -Finstallation_url=$(INSTALLATIONURL) \
#	 $(PRODUCTURL)/$(VERSIONNO)/newsitem_edit
#
#zdoannounce-configure:
#	@echo configuring $(NEWSITEM) properties
#	(echo -e \
#	'Zwiki version $(VERSIONNO) has been released.\n\
#	\n\
#	Download: \n\
#	"http://zwiki.org/releases/$(FILE)":http://zwiki.org/releases/$(FILE) or\n\
#	"http://zope.org/Members/simon/ZWiki/$(FILE)":http://zope.org/Members/simon/ZWiki/$(FILE)\n\
#	\n\
#	More information: \n\
#	"http://zwiki.org":http://zwiki.org \n\
#	"http://zwiki.org/KnownIssues":http://zwiki.org/KnownIssues \n\
#	'; \
#	echo "/^\(\w.*\)\?$(VERSIONNO)/;/^\w/-1p" | ed -s CHANGES.txt \
#	) | curl -nsSo.curllog -F'text=<-' -Ftitle="$(PRODUCT) $(VERSIONNO) released" -FNewsItem_topics=Announcement -F"format=Structured Text" $(PRODUCTURL)/$(NEWSITEM)/editItem
#
#zdo-newsitem-publish:
#	@echo publishing the $(VERSIONNO) News Item on zope.org
#	curl -nsS \
#
#zdo-newsitem-retract:
#	@echo retracting the $(VERSIONNO) News Item on zope.org

