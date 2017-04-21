import unittest
from test_core import TestCore
from test_use_cases import TestUseCases


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestCore())
    suite.addTest(TestUseCases())
    return suite


if __name__ == '__main__':
    unittest.main()
