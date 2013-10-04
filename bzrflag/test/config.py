#!/usr/bin/env python
import magictest

from .. import config

import os
pwd = os.path.dirname(__file__)
wf = os.path.join(pwd, 'test.bzw')

class Test(magictest.MagicTest):
    def runTest(self):
        # basic...
        args = '--world=test_bad.bzw --green-port=50189'.split()
        self.assertRaises(config.ArgumentError, config.Config,args)
        args[0] = '--world='+os.path.join(pwd, 'test.bzw')
        c = config.Config(args)
        self.assertRaises(Exception,config.Config)
        self.assertEquals(c['world'],wf)
        self.assertEquals(c['green_port'], 50189)

suite = Test.toSuite()
# vim: et sw=4 sts=4
