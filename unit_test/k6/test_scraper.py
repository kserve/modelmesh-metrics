import unittest
from perf_test.scripts import scraper

# Tests to make sure that natural sort behaves the way that it should.
# If this breaks, the results will be a in a semi-random order.
class naturalSortValidationTests(unittest.TestCase):
    def test_empty_natural_sort(self):
        self.assertEqual([], scraper.natural_sort([]))

    def test_arbitrary_natural_sort(self):
        filenames = [
            'render/foo_1.txt',
            'render/foo_2.txt',
            'render/foo_10.txt',
            'render/foo_5.txt',
            'render/foo_3.txt'
        ]
        expected = [
            'render/foo_1.txt',
            'render/foo_2.txt',
            'render/foo_3.txt',
            'render/foo_5.txt',
            'render/foo_10.txt'
        ]
        self.assertEqual(expected, scraper.natural_sort(filenames))

if __name__ == '__main__':
    unittest.main()