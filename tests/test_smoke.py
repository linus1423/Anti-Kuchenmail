import sys
import unittest

import guard


class SmokeTest(unittest.TestCase):
    def test_package_imports_with_version(self):
        self.assertRegex(guard.__version__, r"^\d+\.\d+\.\d+$")

    def test_python_is_new_enough(self):
        self.assertGreaterEqual(sys.version_info[:2], guard.MIN_PYTHON)


if __name__ == "__main__":
    unittest.main()
