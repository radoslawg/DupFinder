import unittest
from unittest import mock
import DupFinder.fs
import DupFinder.db


class TestFileDup(unittest.TestCase):

    def test_create_db(self):
        db = DupFinder.db.create_db(":memory:")
        cur = db.cursor()
        cur.execute("SELECT * from dupfinder")
        description = [x[0] for x in cur.description]
        cur.close()
        self.assertEqual(['filepath', 'size', 'hash'], description)
        db.close()

    @mock.patch('os.path.isfile')
    def test_create_db_file_exists(self, mock_isfile):
        """
        Tries to create db in as a file that already exists on disk.
        It mocks os.path.isfile to simulate file already existing.
        """
        mock_isfile.return_value = True
        db = DupFinder.db.create_db("test")
        self.assertIsNone(db)

    def test_connect_db_memory(self):
        """
        Connection to memory DB is not really sane. Use
        DupFinder.db.create_db(':memory:') for that.
        """
        db = DupFinder.db.connect_db(":memory:")
        self.assertIsNone(db)

    @mock.patch('os.path.isfile')
    def test_connect_db_file(self, mock_isfile):
        """
        Connect to non-existing db returns None
        """
        mock_isfile.return_value = False
        db = DupFinder.db.connect_db("test")
        self.assertIsNone(db)

    def test_add_entry_none_db(self):
        """
        If something is wrong with item or db it should not add entry
        """
        entry = DupFinder.db.add_item(None, None)
        self.assertFalse(entry)
        db = DupFinder.db.create_db(":memory:")
        entry = DupFinder.db.add_item(db, None)
        self.assertFalse(entry)
        db.close()

    def test_add_entry_to_db(self):
        """
        Try to add valid entry to valid db should succeed and be fetch back,
        because that is how DBs generally work.
        """
        db = DupFinder.db.create_db(":memory:")
        item = {'filepath': 'something', 'size': 100, 'hash': 'abcdef'}
        r = DupFinder.db.add_item(db, item)
        self.assertTrue(r)
        cur = db.cursor()
        cur.execute("SELECT * from dupfinder")
        self.assertEqual(item, cur.fetchone())

    def test_add_items_to_db(self):
        db = DupFinder.db.create_db(":memory:")
        items = [{'filepath': 'something', 'size': 100, 'hash': 'abcdef'},
                 {'filepath': 'foobar', 'size': 200, 'hash': 'xyz'}]
        DupFinder.db.add_items(db, items)
        cur = db.cursor()
        cur.execute("SELECT * from dupfinder")
        self.assertEqual(items[0], cur.fetchone())
        self.assertEqual(items[1], cur.fetchone())
        cur.close()
        db.close()
