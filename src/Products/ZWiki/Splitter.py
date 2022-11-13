# A simple unicode splitter for ZCTextIndex

from Products.ZCTextIndex.PipelineFactory import element_factory
import re

# Credits:
# The following code is mostly taken from the
# UnicodeLexicon product by Stefan H. Holek (ZPL)
# which can be found at:
# http://www.zope.org/Members/shh/UnicodeLexicon
# Many thanks to you Stefan!

# We are using this here, so people with minimal needs don't
# have to install extra products. If you need more than this
# install a more specific splitter (e.g. a CJK splitter)
# create a new "ZCTextIndex Lexicon" and recreate the
# "SearchableText" and "Title" indexes with your new lexicon

enc = 'utf-8'


class UnicodeWordSplitter:

    word = re.compile(r"(?u)\w+")
    wordGlob = re.compile(r"(?u)\w+[\w*?]*")
    html = re.compile(r"(?u)<[^<>]*>|&[A-Za-z0-9#]+;")

    def process(self, lst, glob=False, strip_html=False):
        result = []
        for w in lst:
            if not isinstance(w, unicode):
                w = unicode(w, enc)
            if strip_html:
                w = self.html.sub(' ', w)
            if glob:
                result += self.wordGlob.findall(w)
            else:
                result += self.word.findall(w)
        return result

    def processGlob(self, lst):
        return self.process(lst, True)


class UnicodeHTMLWordSplitter(UnicodeWordSplitter):

    def process(self, lst, glob=False):
        return UnicodeWordSplitter.process(self, lst, glob, True)


class UnicodeCaseNormalizer:

    def process(self, lst):
        result = []
        for w in lst:
            if not isinstance(w, unicode):
                w = unicode(w, enc)
            result.append(w.lower())
        return result


try:
    element_factory.registerFactory('Word Splitter',
          'Unicode Whitespace splitter', UnicodeWordSplitter)
    element_factory.registerFactory('Word Splitter',
          'Unicode HTML aware splitter', UnicodeHTMLWordSplitter)
    element_factory.registerFactory('Case Normalizer',
          'Unicode Case normalizer', UnicodeCaseNormalizer)
except ValueError:
    # in case the splitter is already registered, ValueError is raised
    pass

