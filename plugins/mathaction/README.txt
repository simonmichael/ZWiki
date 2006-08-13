LatexWiki readme

 This zope product is a patch to "ZWiki":http://zwiki.org that allows
 you to include LaTeX markup in wiki pages.  LaTeX is a document
 typesetting system based on !TeX; information is available at the
 "Latex project homepage":http://www.latex-project.org/.  LatexWiki
 adds a new !ZWikiPage type called "stxlatex" which renders
 "Structured Text":http://www.zope.org/Documentation/Articles/STX
 with inline LaTeX and replaces the markup with an image.

 This product requires 

   * "Zope 2.6":http://www.zope.org/ or later
   
   * Python 2.2 or later

   * the "ZWiki 0.32":http://www.zwiki.org/ Zope product

   * the "LocalFS":http://www.zope.org/Members/jfarr/Products/LocalFS
     Zope product 

   * "Ghostscript 6.0.5":http://www.ghostscript.com/ or later with the
     following options compiled in (which is the case in most
     installations of Ghostscript)

     * PNG output device support

   * A working LaTeX installation including latex and dvips (we use
     "teTex":http://www.tug.org/teTeX/)

   * The "Python Imaging Library":http://www.pythonware.com/products/pil/

 For those running large distributions such as Red Hat Linux, many of
 the necessary tools (Ghostscript, LaTeX) are probably already installed. For
 those running FreeBSD, you will find the necessary items in the ports tree.
 Your mileage may vary. 

 Information on installing LatexWiki is in the INSTALL.txt file.

 This product has been tested on FreeBSD 4.2 and Zope 2.4.1.  It has also been
 tested on Zope 2.6.1 and ZWiki 0.14 under Debian.

 (c) 2001 Open Software Services <info@OpenSoftwareServices.com>
 portions (c) 2003 Bob McElrath <bob+latexwiki@mcelrath.org>
 This product is available under the GPL - see LICENSE.txt
 All rights reserved, all disclaimers apply, etc.

NEW NOTES:

pamphlet pages:
- install dvipng
- install http://daly.axiom-developer.org/axiom.sty as /usr/local/share/texmf/tex/latex/axiom.sty and run mktexlsr
