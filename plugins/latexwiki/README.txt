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

   * Zope >=2.9 (http://www.zope.org)
   
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
items in the ports tree.  Debian/Ubuntu users, try::

  apt-get install tetex-base tetex-bin tetex-extra gs zope2.9 python-imaging dvipng


Installing
----------

Make sure that you have the requirements installed (above) and follow the
instructions at http://zwiki.org/LatexWiki .
     
Other notes:

 * You may get better results if you add the properties
   'latex_font_size' (int), 'latex_align_fudge' (float),
   'latex_res_fudge' (float), and 'allow_dtml' (boolean) to your wiki
   folder(s) (and set them to.. ?).  It may be useful to create a new
   wiki using the latexwiki template for comparison.
