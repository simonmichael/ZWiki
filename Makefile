# Zwiki/zwiki.org makefile


# RELEASE SCRIPT (CVS)
# ----------------------------------------
# IN TRUNK   # IN BRANCH
# check all in, check tests, check tracker, check docs
#  (README,dtml/*,content/*,zwiki.org/HelpPage,QuickReference,showAccessKeys)
# make changelog, update CHANGES.txt and commit
# RC1 ONLY:
#  remove cvs from version.txt
#  make releasebranch
#  (later) bump version.txt to 0-WW-0cvs, make version
             # RC2 ONWARDS:
             #  make sure all branch fixes checked in and merged to trunk, including CHANGES.txt
             #  selectively tag and merge trunk changes, including CHANGES.txt: 
             #   how to get a list of trunk changes ?
             #   cvs tag -cF -r HEAD merge-0-VV-0rcB ... (in trunk)
             #   RC2:  cvs update -j release-0-VV-fork -j merge-0-VV-0rcB ...
             #   RC3+: cvs update -j merge-0-VV-0rcA -j merge-0-VV-0rcB ...
             # bump version.txt, make version
             # (check tests, check tracker)
             # cvs commit -m 'merge fixes to release-0-VV-branch'
             # make release
# make push
# update FrontPage,KnownIssues,OldKnownIssues,ReleaseNotes,GeneralDiscussion,#zwiki
# FINAL RELEASE:
# mail announcement to zope-announce@zope.org, zwiki@zwiki.org

# NEW RELEASE SCRIPT (darcs)
# simple no-branch version:
# ----------------------------------------
# record all
# check tests
# check tracker
# check docs (showAccessKeys,README,dtml/*,content/*, zwiki.org HelpPage,QuickReference)
# update CHANGES.txt from darcs changes, add release date/version
# update version.txt, make version
# record all
# check tests
# tag release
# build tarball
# push all
# update FrontPage,KnownIssues,OldKnownIssues,ReleaseNotes,discussion,#zwiki
# final: send mail to zope-announce@zope.org, zwiki@zwiki.org

HOST=zwiki.org
LHOST=localhost:9673
CURL=curl -o.curllog -sS -n
PRODUCT=ZWiki
CVSMODULE=zwiki
# info for zope.org 
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

## bits and pieces

help: 
	cat Makefile

changelog:
	cvs2cl --follow trunk --day-of-week
	cvs commit -m 'latest' ChangeLog

CLEAN=perl -p -e "s/(?s)^\#parents:.*?\n//;"
skinviews:
	@echo regenerating skin views from dtml pages
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

## upload to server (rsync)

rcheck:
	rsync -ruvC -e ssh --include=ChangeLog --include=misc \
	  --include=releases  -n . zwiki.org:zwiki

rpush:
	rsync -ruvC -e ssh --include=ChangeLog --include=misc \
	  --include=releases . zwiki.org:zwiki

## upload to server (darcs push)

check: 
	darcs whatsnew

summary: 
	darcs whatsnew --summary

push:
	darcs push -v -a

## server control

restart:
	@echo restarting zope on $(HOST)
	ssh $(HOST) '/instance/zope_stop;sleep 1;/instance/zope_start'
#	curl -n -sS -o.curllog 'http://$(HOST)/Control_Panel/manage_restart'

lrefresh: lrefresh-$(PRODUCT)

lrefresh-%:
	@echo refreshing product $* on $(LHOST)
	curl -n -sS -o.curllog 'http://$(LHOST)/Control_Panel/Products/$*/manage_performRefresh'

refresh: refresh-$(PRODUCT)

refresh-%:
	@echo refreshing $* product on $(HOST)
	@$(CURL) 'http://$(HOST)/Control_Panel/Products/$*/manage_performRefresh'

refresh-mailin:
	@echo refreshing mailin.py external method on $(HOST)
	@$(CURL) 'http://$(HOST)/mailin/manage_edit?id=mailin&module=mailin&function=mailin&title='

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

#analyzezodb:
#	ssh zwiki.org 'export ZOPEVERSION=2.6.1; export ZOPEHOME=/usr/local/zope/$$ZOPEVERSION; export INSTANCE_HOME=/usr/local/zope/instance; export SOFTWARE_HOME=$$ZOPEHOME/lib/python; export PYTHONPATH=$$SOFTWARE_HOME:$$ZOPEHOME:$$INSTANCE_HOME; /usr/local/bin/ZODBAnalyze.py ~simon/var/Data.fs >~simon/ZWiki/zodb_report.txt'


## branching, releasing

VERSION:=$(shell cut -c7- version.txt )
MAJORVERSION:=$(shell echo $(VERSION) | sed -e's/-[^-]*$$//')
VERSIONNO:=$(shell echo $(VERSION) | sed -e's/-/./g')
FILE:=$(PRODUCT)-$(VERSIONNO).tgz

version:
	@echo setting version to $(VERSIONNO)
	perl -pi -e "s/__version__='.*?'/__version__='$(VERSIONNO)'/" __init__.py
	perl -pi -e "s/Zwiki version [0-9a-z.-]+\./Zwiki version $(VERSIONNO)./"\
	  content/basic/HelpPage.stx

releasebranch: mergetag
	cvs tag -F release-$(MAJORVERSION)-fork
	cvs tag -Fb release-$(MAJORVERSION)-branch
	cd ~; cvs -d:ext:simon@cvs.zwiki.sourceforge.net:/cvsroot/zwiki \
	 checkout -r release-$(MAJORVERSION)-branch -d zwiki-$(VERSIONNO) zwiki
	cd ~/zwiki-$(VERSIONNO); \
	 cvs remove -f ChangeLog; \
	 echo $(PRODUCT)-$(MAJORVERSION)-0rc1 >version.txt; \
	 make version; \
	 echo XXX now:
	 echo \> cvs commit -m '$(VERSIONNO)rc1'; \
	 echo \> make release

mergetag:
	#this must be in progress..
	#@echo do: cvs tag -cF -r HEAD merge-$(VERSION)+1

mergeuntag:
	#@echo do: cvs tag -d -r HEAD merge-$(VERSION)+1

releasetag:
	cvs tag -cF release-$(VERSION)

releaseuntag:
	cvs tag -d release-$(VERSION)

release: clean releasetag
	rm -f $(HOME)/zwiki/releases/$(FILE)
	cvs export -r release-$(VERSION) -d $(PRODUCT) $(CVSMODULE)
	find $(PRODUCT) -name Makefile -o -name TAGS -o -name ChangeLog \
	  |xargs rm -f
	tar -czvf $(HOME)/zwiki/releases/$(FILE) $(PRODUCT)
	rm -rf $(PRODUCT)

releasepush: release
	cd ~/zwiki; make push

############### ZOPE.ORG ###############
# automating the intricacies of zope.org
NEWSITEM=$(PRODUCT)-$(VERSION)-released

zdo-release: zdo-swrelease zdo-swreleasefile

#zdo-newsitem: 

zdo-swrelease: zdo-swrelease-create zdo-swrelease-edit \
	zdo-swrelease-metadata zdo-swrelease-publish

zdo-swreleasefile: zdo-swreleasefile-create zdo-swreleasefile-edit \
	zdo-swreleasefile-metadata zdo-swreleasefile-publish

## Software Packages

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

## Software Releases

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


## Software Release Files

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


## News Items
#
#do-newsitem-create:
#	@echo creating the $(VERSIONNO) News Item on zope.org
#	@curl -nsS \
#	 -Fid=$(VERSIONNO)
#	 -Ftitle=''
#	 -Ffile=@$(HOME)/zwiki/releases/$(FILE)
#	 $(PRODUCTURL)/manage_addProduct/ZopeSite/Release_factory/Release_add
#
#doannounce-create:
#	@echo creating $(NEWSITEM) news item on zope.org
#	@curl -nsSo.curllog -Fid=$(NEWSITEM) -Ftitle="" -Ftext="" -F"submit= Add " $(PRODUCTURL)/manage_addProduct/ZopeSite/fNewsItem/addNewsItem
#
#do-newsitem-configure:
#	@echo configuring the $(VERSIONNO) News Item on zope.org
#	curl -nsSo.curllog \
#	 -Fname=$(VERSIONNO) \
#	 -Finfo_url=$(INFOURL) \
#	 -Fchanges_url=$(CHANGESURL) \
#	 -Flicense_url=$(LICENSEURL) \
#	 -Finstallation_url=$(INSTALLATIONURL) \
#	 $(PRODUCTURL)/$(VERSIONNO)/newsitem_edit
#
#doannounce-configure:
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


########################################

## tags & cleanup

tags:
	find $$PWD/ -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
	  -o -name _darcs  -prune -type f \
	  -o -name contrib -prune -type f \
	  -o -name misc    -prune -type f \
	  -o -name old     -prune -type f \
	  | xargs etags
# |xargs eptags didn't work at one point
#	~/bin/etags.py \
#	  `find $$PWD/ -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
#	     -o -name _darcs     -prune -type f \
#	     -o -name old     -prune -type f \
#	     -o -name contrib -prune -type f \
#	     -o -name misc    -prune -type f`

zopetags:
	cd /usr/lib/zope/lib/python; \
	  ~/bin/eptags.py `find $$PWD -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

producttags:
	cd /var/lib/zope/Products; \
	  ~/bin/eptags.py `find $$PWD -name '*.py' -o  -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

alltags: tags producttags zopetags
	cat TAGS /var/lib/zope/Products/TAGS /usr/lib/zope/lib/python/TAGS \
	 >TAGS.all

plonetags:
	cd /var/lib/zope/Products/CMFPlone; \
	  ~/bin/eptags.py \
	  `find $$PWD -name '*.py' -o -name '*.dtml' -o -name '*.pt' \
	     -o -name old     -prune -type f `

clean:
	rm -f .*~ *~ *.tgz *.bak

Clean: clean
	rm -f locale/*.mo


## misc automation

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

# i18n

LANGUAGES=en es fr-CA fr ga

# using zope 3's i18nextract.py with my patches (-x option, multiline defaults fix)
pot:
	PYTHONPATH=/usr/local/src/Zope3/src python \
	  /usr/local/src/Zope3/utilities/i18nextract.py -d zwiki -p . -o ./i18n \
	    -x _darcs -x old -x misc -x ftests 
	# ----------------------------------
	# now do fixups to zwiki.pot:
	# 1. update license & Language-Team
	# 2. add meta data required by PTS:
	# "Language-code: xx\n"
	# "Language-name: X\n"
	# "Preferred-encodings: utf-8 latin1\n"
	# "Domain: zwiki\n"
	# ----------------------------------

po:
	cd i18n; \
	for L in $(LANGUAGES); do \
	 echo $$L; msgmerge -U $$L.po zwiki.pot; done

mo:
	cd i18n; \
	for L in $(LANGUAGES); do \
	 echo $$L; msgfmt --statistics $$L.po -o $$L.mo; done


# old: junk you have to remove after a CVS checkout:
# content/cmf
# default_wiki_content
# emacs
# import
# locale
# skins/{css,wiki,zpt_wiki,zwiki_cmf,zwiki_orig}
# templates
# wikis
