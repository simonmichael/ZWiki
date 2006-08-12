This zope product is a patch to Zwiki (http://zwiki.org) that allows you
to include LaTeX markup in wiki pages.  LaTeX is a document typesetting
system based on TeX; information is available at the Latex project
homepage (http://www.latex-project.org).  LatexWiki adds a new zwiki page
type called "stxlatex" which renders Structured Text
(http://www.zope.org/Documentation/Articles/STX) with inline LaTeX and
replaces the markup with an image. 
(**disabled** Also included are an HTML+LaTeX mode and an itex (MathML) mode.)


Installing
==========

This version of LatexWiki has been tested with 

   * Zope 2.9.x (http://www.zope.org)
   
   * Python 2.4.x

   * Zwiki 0.52 (http://zwiki.org) Zope product

   * LocalFS 1.7-andreas (http://www.easyleading.org/Downloads)

   * Ghostscript 7.0.x (http://www.ghostscript.com) with support for the
     PNG output device

   * A working LaTeX installation including latex and dvips (we use
     teTex (http://www.tug.org/teTeX) )

   * The Python Imaging Library (http://www.pythonware.com/products/pil)

   * The dvipng (http://sourceforge.net/projects/dvipng) utility (optional --
     but a big speed improvement (actually, I got an error without it))

For those running large distributions such as Red Hat Linux, many of
the necessary tools (Ghostscript, LaTeX) are probably already installed. For
those running FreeBSD, you will find the necessary items in the ports tree.
In debian-based systems try::

 apt-get install tetex-base tetex-bin tetex-extra gs zope2.9 python-imaging dvipng


Installing LatexWiki (Standalone)
---------------------------------

  1. Make sure that you have the required components installed (see
     above). Up-to-date versions of ZWiki and LocalFS will probably need
     to be installed manually.  (Just untar them into the Products
     directory, similar to step 2)

  2. Unpack the LatexWiki distribution into your Zope installation's
     Products directory (usually /usr/lib/zope/lib/python/Products) with a
     command such as::

       tar -zxvf LatexWiki-0.53.tar.gz

  3. If you do not already have a Wiki, create one by going to the Zope
     management interface and selecting ZWiki from the pulldown in the
     upper right.  For "Type", select "latexwiki".
     **WARNING: disabled, instead copy or symlink
     LatexWiki/wikis/latexwiki to ZWiki/wikis/latexwiki**
     

Installing LatexWiki in Plone 
-----------------------------

**WARNING: CMF/Plone support code needs review & updating**

(See also: "PloneAndCMF":http://zwiki.org/Chapter13PloneAndCMF)

  1. Do steps 1 and 2 above.

  2. Install the CMF Quick Installer (included with Plone 2.0)
  
  3. Create a 'Plone Site' from the dropdown in the ZMI.

  4. Add a 'CMF Quick Installer' tool to your new plone site.

  5. Click on this new plone_cmfquickinstaller node in the ZMI.  You should see
      both ZWiki and LatexWiki.  Install both.  
      
  6. Create a ZWiki Page.  You will have to press shift-reload in your browser
     when viewing this new page in order to get the new latexwiki stylesheets
     that get installed in step 5.

I recommend removing one of the two sidebars in Plone.  LatexWiki requires a
somewhat large font to make latex readable, which looks bad when put into
Plone's narrow document window between two sidebars.  

To do this: 

        1. Go to your plone folder in the ZMI

        2. Click the "Properties" tab

        3. Delete the lines in either the "right_slots" or "left_slots"
           properties.

Installing itex with LatexWiki
------------------------------

**WARNING: itex support is currently disabled**

MathML support is included in the form of
"itex2MML:http://golem.ph.utexas.edu/~distler/blog/itex2MML.html, which
does not use latex, but will render a large subset of LaTeX math markup
into MathML.  To use this:

  1. Install the itex binary somewhere in your path that is seen by
     zope.  (I use /usr/local/bin/)

  2. After adding a ZWiki in the ZMI, go to the "Properties" tab of your
     new wiki.  Add a "string" attribute::

        name: zwiki_content_type
        value: application/xhtml+xml;charset=utf-8


Upgrading
=========

**WARNING: this information may be incomplete**

LatexWiki 0.25
--------------

 * You will have to add the properties 'latex_font_size' (int),
   'latex_align_fudge' (float), 'latex_res_fudge' (float), and 'allow_dtml'
   (boolean) to your wiki folder(s).  It may be useful to create a latexwiki
   from the template (see INSTALL.txt, step 3) for comparison.

 * If you are using Ape or something else (FileSystemSite?) to allow access to
   the images/ directory, this will still work but the site template will try
   to create a LocalFS images directory.  Just delete it and replace it with
   Ape, or whatever.  Appropriate patches to Extensions/setup_latexwiki.py
   would be appreciated.

LatexWiki 0.22
--------------

 * remove editform,  RecentChanges, SearchPage, UserOptions, IssueTracker, and
   FilterIssues if you have them.

 * You may have to modify files which make reference to any of the above pages.
   They are all now methods that can be called like:
        <a href="&dtml-wiki_page_url;/recentchanges">Recent Changes</a>

 * If you have just added the stylesheet for the first time (see INSTALL.txt),
   you may need to add:
       <link rel="stylesheet" href="stylesheet">
   to your standard_wiki_header.  (Newer wikis do not have the standard_wiki_header)

 * DO NOT DOWNGRADE.  ZWiki 0.25 changes page types fundamentally, and your
   wiki will be broken if you downgrade to an older version of ZWiki.



(c) 2001 Open Software Services <info@OpenSoftwareServices.com>
portions (c) 2003,2004,2005 Bob McElrath <bob+latexwiki@mcelrath.org>
This product is available under the GPL - see LICENSE.txt
All rights reserved, all disclaimers apply, etc.
