#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.discover(Path(__file__).parent, pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite).wasSuccessful()


if __name__ == '__main__':
    sys.exit(0 if run_all_tests() else 1)
