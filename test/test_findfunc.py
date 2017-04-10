#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" test_findfunc.py
    Unit tests for findfunc.py.

    -Christopher Welborn 04-09-2017
"""

import os
import re
import sys
import unittest

from findfunc import (
    find_func,
)
testpath = os.path.abspath(__file__)
testdir = os.path.split(testpath)[0]
pkgdir = os.path.split(testdir)[0]

findfunc_path = os.path.join(pkgdir, 'findfunc/tools.py')
has_findfunc_src = os.path.exists(findfunc_path)


class TestCase(unittest.TestCase):

    @unittest.skipUnless(has_findfunc_src, 'Missing findfunc source file.')
    def test_find_func_file_arg(self):
        """ find_func should handle open files, or file paths. """
        pat = re.compile('find_func')
        # File path.
        defs = list(find_func(findfunc_path, pat))
        self.assertGreater(
            len(defs),
            0,
            msg='Failed to find ANY function definitions for file path.',
        )
        # File object.
        with open(findfunc_path) as f:
            defs = list(find_func(f, pat))
        self.assertGreater(
            len(defs),
            0,
            msg='Failed to find ANY function definitions for file object.',
        )


if __name__ == '__main__':
    unittest.main(argv=sys.argv, verbosity=2)
