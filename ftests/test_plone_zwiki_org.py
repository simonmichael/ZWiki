# functional tests for plone.zwiki.org

import os, sys, re, string
import unittest
from curltest import TestBase

SITE='http://plone.zwiki.org'
PAGE=SITE+'/FrontPage'

class AnonTests(TestBase):

    def test_anonymous_can_view_front_page(self):
        self.assertPageContains(SITE,'Welcome to the Zwiki Plone test site.')

    def test_anonymous_cant_add_pages_without_permission(self):
        try: 
            self.assertPageContains(SITE+'/anonreadonly/TestPage/create?page=TestPage1',
                                    '(Unauthorized|Please log in|You are not authorized)')
        finally:
            try: 
                x = self.getPage(SITE+'/anonreadonly/TestPage1/delete',
                                 'member','passwd')
            except: pass

class MemberTests(TestBase):

    def test_member_can_view_front_page(self):
        self.assertPageContains(SITE,'Welcome to the Zwiki Plone test site.',
                                'member','passwd')


class ManagerTests(TestBase):

    def test_manager_can_view_front_page(self):
        self.assertPageContains(SITE,'Welcome to the Zwiki Plone test site.',
                                'manager','passwd')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AnonTests))
    suite.addTest(unittest.makeSuite(MemberTests))
    suite.addTest(unittest.makeSuite(ManagerTests))
    return suite

if __name__ == '__main__': 
    unittest.TextTestRunner().run(test_suite())
