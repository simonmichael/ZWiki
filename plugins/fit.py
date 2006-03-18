# fit (framework for interactive testing) support

import sys, os, string, re

from AccessControl import getSecurityManager, ClassSecurityInfo
from Globals import InitializeClass
from OFS.DTMLDocument import DTMLDocument

from Products.ZWiki import Permissions
from Products.ZWiki.plugins import registerPlugin
from Products.ZWiki.Defaults import registerPageMetaData
from Products.ZWiki.Utils import Popen3, formattedTraceback, BLATHER
from Products.ZWiki.Views import addErrorTo

# from testsupport.py:
def pdir(path): return os.path.split(path)[0]
ZWIKIDIR = pdir(os.path.abspath(__file__))

def hasFitTests(self):
    """
    Does this page have any tables containing fit tests ?

    Should match python fit's regexp.
    """
    return re.search(r'([Ff]ixtures|\bfit)\.\w',self.read()
                     ) is not None

# fit may not be installed, but we need to provide a stub class 
# for the moment IIRC
try:
    from fit.Parse import Parse
    from fit.Parse import ParseException
    from fit.Fixture import Fixture
    class PluginFit:
        """
        Mix-in class for fit support
        """
        security = ClassSecurityInfo()

        def _runFitInternallyOn(self,text):
            try:
                fitTables = Parse(text)
            except ParseException:
                return text

            # reset class-variable counts
            # not working
            Fixture.rights = 0
            Fixture.wrongs = 0
            Fixture.ignores = 0
            Fixture.exceptions = 0
            Fixture.summary = {}

            # find fit in ZWiki product directory as well as PYTHONPATH
            oldpath = sys.path
            sys.path.insert(0,ZWIKIDIR)

            Fixture().doTables(fitTables)

            sys.path = oldpath
            return str(fitTables)

        def _runFitExternallyOn(self,text):
            oldpath = sys.path
            sys.path.insert(0,ZWIKIDIR)
            p = Popen3(
                '''PYTHONPATH=%s python -c \
                     "import fit.FileRunner; \
                      fit.FileRunner.FileRunner(('','-','-')).run()"''' % \
                  string.join(sys.path,':'),
                input=text)
            sys.path = oldpath
            return p.out

        #def _runFitOnClassFit(self,text):
        #    """
        #    Run fit on tables with class="fit".
        #    """
        #    # jiggery-pokery
        #    t = text
        #    t = re.sub(r'(?im)<table class="fit"',r'<_fittable',t)
        #    t = re.sub(r'(?im)<table',r'<_ordinarytable',t)
        #    t = re.sub(r'(?im)<_fittable',r'<table class="fit"',t)
        #    t = self._runFitInternallyOn(t)
        #    t = re.sub(r'(?im)<_ordinarytable',r'<table',t)
        #    return t

        def runFitTestsIn(self,text):
            """
            Run fit on tables in text.

            Modified fit to test only certain tables (though it parses all).
            """
            return self._runFitInternallyOn(text)

        security.declareProtected(Permissions.View, 'hasFitTests')
        def hasFitTests(self): return hasFitTests(self)


except ImportError:
    BLATHER('did not find fit in the PYTHONPATH, skipping')
    class PluginFit:
        security = ClassSecurityInfo()
        security.declareProtected(Permissions.View, 'hasFitTests')
        def hasFitTests(self): return hasFitTests(self)
        def runFitTestsIn(self,text): return text

InitializeClass(PluginFit)
registerPlugin(PluginFit)
