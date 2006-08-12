This is the latexwiki plugin for Zwiki, based on the earlier LatexWiki
product and patch, that allows you to include LaTeX markup in Zwiki
pages.  LaTeX is a document typesetting system based on TeX;
information is available at the LaTeX project homepage
(http://www.latex-project.org).

The plugin adds a new zwiki page type, "Structured Text + LaTeX"
(stxlatex), which renders Structured Text
(http://www.zope.org/Documentation/Articles/STX) and inline LaTeX,
replacing the latter with appropriate images.  

See LICENSE.txt for copyright and license information.


Requirements
============

This Zwiki+latexwiki version has been tested with 

   * Zope 2.9.x (http://www.zope.org)
   
   * Python 2.4.x

   * LocalFS 1.7-andreas (http://www.easyleading.org/Downloads)

   * Ghostscript 7.0.x (http://www.ghostscript.com) with support for the
     PNG output device

   * A working LaTeX installation including latex and dvips (we use
     teTex (http://www.tug.org/teTeX) )

   * The Python Imaging Library (http://www.pythonware.com/products/pil)

   * The dvipng (http://sourceforge.net/projects/dvipng) utility (optional --
     but a big speed improvement (actually, I got an error without it))

For those running large distributions such as Red Hat Linux, many of
the necessary tools (Ghostscript, LaTeX) are probably already
installed. For those running FreeBSD, you will find the necessary
items in the ports tree.  In debian-based systems try::

  apt-get install tetex-base tetex-bin tetex-extra gs zope2.9 python-imaging dvipng


Installing LatexWiki standalone
-------------------------------

  1. Make sure that you have the required components installed (see
     above) and just install Zwiki as usual. LocalFS will probably
     need to be installed manually.  (Just untar it into the Zope
     Products directory.)

  2. If you do not already have a Wiki, create one by going to the Zope
     management interface and selecting ZWiki from the pulldown in the
     upper right.  For "Type", select "latexwiki".
     **WARNING: disabled, for now just make a basic wiki.**
     

Installing LatexWiki in Plone 
-----------------------------

**WARNING: CMF/Plone support code needs review & updating**

See also http://zwiki.org/PloneAndCMF .

  1. If needed, create a 'Plone Site' from the dropdown in the ZMI.

  2. Install Zwiki in your plone site using Plone's add/remove products.

  3. If needed, create a Wiki Page.  You may have to press
     shift-reload in your browser when viewing this new page in order
     to get the new latexwiki stylesheets that get installed in step
     2.

I recommend removing one of the two sidebars in Plone.  LatexWiki
requires a somewhat large font to make latex readable, which looks bad
when put into Plone's narrow document window between two sidebars.  To
do this:

  1. Go to your plone folder in the ZMI

  2. Click the "Properties" tab

  3. Delete the lines in either the "right_slots" or "left_slots" properties.


Other notes
-----------

 * You may get better results if you add the properties
   'latex_font_size' (int), 'latex_align_fudge' (float),
   'latex_res_fudge' (float), and 'allow_dtml' (boolean) to your wiki
   folder(s) (and set them to.. ?).  It may be useful to create a new
   wiki using the latexwiki template for comparison.

 * If you are using Ape or something else (FileSystemSite?) to allow access to
   the images/ directory, this will still work but the site template will try
   to create a LocalFS images directory.  Just delete it and replace it with
   Ape, or whatever.  Appropriate patches to Extensions/setup_latexwiki.py
   would be appreciated.
