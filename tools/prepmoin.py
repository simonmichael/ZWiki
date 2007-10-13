#!/usr/bin/python2.4

import sys
import os
import fnmatch
import shutil
import re

def usage(exitcode, errmsg=None):
	print "Usage: %s </path/to/moinmoin/wiki/data> </path/to/exported/moinmoin/files> <http://your.zwiki.com/url>" % (sys.argv[0])
	print "	/path/to/moinmoin/wiki/data must exist, and point to the actual files used by a MoinMoin wiki"
	print "	/path/to/exported/moinmoin/files must not exist"
	print " http://your.zwiki.com/url is the URL that will host your exported wiki"
	if errmsg is not None:
		print ""
		print "Usage error was %s" % (errmsg)
	if exitcode != 0:
		sys.exit(exitcode)

def locate(pattern, root=os.curdir):
	for path, dirs, files in os.walk(os.path.abspath(root)):
		for filename in fnmatch.filter(files, pattern):
			yield os.path.join(path, filename)

if len(sys.argv) != 4:
	usage(1)

srcdir  = sys.argv[1]
destdir = sys.argv[2]
desturl = "file: %s" % (sys.argv[3])
attachreg = re.compile("attachment:")

if not(os.path.exists(srcdir)):
	usage(2, "Wiki source directory must exist, and %s does not exist" % (srcdir))

if not(os.path.isdir(srcdir)):
	usage(3, "Wiki source must be a directory, and %s is not a wiki source directory" % (srcdir))

if not(os.path.exists(os.path.join(srcdir, "data"))):
	usage(4, "Directory %s does not have a data directory, which means it does not look like a MoinMoin wiki to me" % (srcdir))

if os.path.exists(destdir):
	usage(5, "Destination must not exist, and %s does exist." % (destdir))

try:
	os.mkdir(destdir)
except OSError:
	usage(6, "Error making the destination directory %s" % (destdir))

for file in locate("current", os.path.join(srcdir, "data")):
	src = os.path.split(file)[0]
	destfile = os.path.join(destdir, "%s%s" % (os.path.split(src)[1], ".moin"))
	vin = open(file, "r")
	rev = vin.readline().strip()
	vin.close()
	moinfile = os.path.join(src, "revisions", rev)
	if os.path.exists(moinfile):
		print "*** Processing %s " % (destfile)
		#shutil.copyfile(moinfile, destfile)
		fin = open(moinfile, "r")
		contents = fin.readlines()
		fin.close()
		out = map(lambda x: attachreg.sub(desturl, x), contents)
		fin = open(destfile, "w")
		fin.writelines(out)
		fin.close()
		for attach in locate("*", os.path.join(src, 'attachments')):
			attachname = os.path.split(attach)[1]
			destattach = os.path.join(destdir, attachname)
			if os.path.exists(destattach):
				print "    --- Warning: Attachment %s already exists in the export directory" % (attachname)
			else:
				print "    +++ Processing %s" % (attachname)
				shutil.copyfile(attach, destattach)
	else:
		print "!!! Missing current revision for %s" % (destfile)

