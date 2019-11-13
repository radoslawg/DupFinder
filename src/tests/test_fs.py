import DupFinder.fs
import DupFinder.db
import os
import pyfakefs
import pytest
import xxhash


def test_enumerate_directory(fs):
    """
    Given directory structure, it would traverse subfolders with recursion
    and return file list. Pytest provdes fs fixture that provide "fake"
    filesystem that we can work on.
    Warning: For some reason this fixture was giving me 'c:' dir when
    enumarating '/' directory. It is not how real thing(tm) works.
    """
    fs.create_file('/phonyDir/file1')
    fs.create_file('/phonyDir/file4')
    fs.create_dir('/phonyDir/dir1')
    fs.create_file('/phonyDir/dir1/file2')
    fs.create_file('/phonyDir/dir1/file3')
    fs.create_dir('/phonyDir/dir1/dir2')
    fs.create_file('/phonyDir/dir1/dir2/file5')
    fs.create_dir('/phonyDir/dir3')
    fs.create_file('/phonyDir/dir3/file6')
    file_list = DupFinder.fs.enumerate_directory('/phonyDir/')
    expected = ['file1', 'file2', 'file3', 'file4', 'file5', 'file6']
    result = [x.name for x in file_list]
    assert sorted(result) == sorted(expected)


def test_index_files(fs):
    """
    Test indexing files in given folder. They should land in database.
    - There should be 6 entries
    - All entries should be hashed
    - No Hash should be identical.
    """
    fs.create_file('/phonyDir/file1', contents='test1')
    fs.create_file('/phonyDir/file4', contents='test2')
    fs.create_dir('/phonyDir/dir1')
    fs.create_file('/phonyDir/dir1/file2', contents='test4')
    fs.create_file('/phonyDir/dir1/file3', contents='test5')
    fs.create_dir('/phonyDir/dir1/dir2')
    fs.create_file('/phonyDir/dir1/dir2/file5', contents='test7')
    fs.create_dir('/phonyDir/dir3')
    fs.create_file('/phonyDir/dir3/file6', contents='test9')
    r = DupFinder.fs.index_files_in_dir('/phonyDir')
    # 6 files in db
    assert len(r) == 6
    # all hashed
    assert [] == [x for x in r if x['hash'] is None or x['hash'] == '']
    # all sizes 5
    assert [] == [x for x in r if x['size'] != 5]
    # no hash is identical
    for i in range(0, len(r)):
        for x in range(i+1, len(r)):
            assert r[i]['hash'] != r[x]['hash']


def test_index_files_wo_hashes(fs):
    fs.create_file('/phonyDir/file1', contents='test1')
    fs.create_file('/phonyDir/file4', contents='test2')
    r = DupFinder.fs.index_files_in_dir('/phonyDir', False)
    assert [] == [x for x in r if x['hash'] is not None]


def test_find_two_ident_file(fs):
    """
    Given we have two files, in different folders, first index one file and
    check that second is identical. Method should return two lists. One with
    files that are suspected of being duplicates, second with new files.
    """
    fs.create_file('/phonyDir/dir1/file1', contents='test')
    fs.create_file('/phonyDir/dir2/file2', contents='test')
    db = DupFinder.db.create_db(":memory:")
    origin = DupFinder.fs.index_files_in_dir('/phonyDir/dir1')
    DupFinder.db.add_items(db, origin)
    new_files = DupFinder.fs.index_files_in_dir('/phonyDir/dir2', False)
    (non_dup, dup) = DupFinder.fs.compare_with_db(db, new_files)
    assert len(non_dup) == 0
    assert len(dup) == 1


def test_find_two_non_ident_file(fs):
    """
    Given we have two files, in different folders, first index one file and
    check that second is diffrent.
    """
    fs.create_file('/phonyDir/dir1/file1', contents='test')
    fs.create_file('/phonyDir/dir2/file2', contents='test2')
    db = DupFinder.db.create_db(":memory:")
    origin = DupFinder.fs.index_files_in_dir('/phonyDir/dir1')
    DupFinder.db.add_items(db, origin)
    new_files = DupFinder.fs.index_files_in_dir('/phonyDir/dir2', False)
    (non_dup, dup) = DupFinder.fs.compare_with_db(db, new_files)
    assert len(non_dup) == 1
    assert len(dup) == 0


def test_find_duplicates(fs):
    """
    Composite of previous tests.
    """
    fs.create_file('/phonyDir/dir2/file1', contents='test1')
    fs.create_file('/phonyDir/dir2/file4', contents='same2')
    fs.create_file('/phonyDir/dir2/dir4/file8', contents='same')
    fs.create_dir('/phonyDir/dir1')
    fs.create_file('/phonyDir/dir1/file2', contents='same')
    fs.create_file('/phonyDir/dir1/file3', contents='test5')
    fs.create_dir('/phonyDir/dir1/dir2')
    fs.create_file('/phonyDir/dir1/dir2/file5', contents='same2')
    fs.create_dir('/phonyDir/dir3')
    fs.create_file('/phonyDir/dir3/file6', contents='same')
    fs.create_file('/phonyDir/dir3/file7', contents='test6')
    db = DupFinder.db.create_db(":memory:")
    origin = DupFinder.fs.index_files_in_dir('/phonyDir/dir1')
    DupFinder.db.add_items(db, origin)
    new_files = DupFinder.fs.index_files_in_dir('/phonyDir/dir2', False)
    (non_dup, dup) = DupFinder.fs.compare_with_db(db, new_files)
    assert len(non_dup) == 1
    assert len(dup) == 2
    assert sorted(
        ['\\phonyDir\\dir2\\file4',
         '\\phonyDir\\dir2\\dir4\\file8']) == sorted([d['filepath'] for d in
                                                      dup])
    assert ['\\phonyDir\\dir2\\file1'] == [d['filepath'] for d in non_dup]


def test_find_duplicates_in_dir(fs):
    """
    Does not use database just checks all the files in directory against each
    other to find duplicates.
    Optionaly it deletes duplicated files except the first one encountered.
    """
    pyfakefs.fake_filesystem.set_uid(0)
    # Setup fs
    fs.create_dir('/phonyDir/dir1')
    fs.create_file('/phonyDir/dir1/this_file_is_duped', contents='same')
    fs.create_file('/phonyDir/dir1/this_file_is_not_duped', contents='test1')
    fs.create_file('/phonyDir/dir1/this_file_is_duped2', contents='same')
    fs.create_dir('/phonyDir/dir1/dir2')
    fs.create_file('/phonyDir/dir1/dir2/this_file_is_duped4', contents='same')
    fs.create_file('/phonyDir/dir1/dir2/this_file_is_not_duped',
                   contents='test3')
    fs.create_file('/phonyDir/dir2/this_file_is_duped3', contents='same')
    fs.create_file('/phonyDir/dir2/this_file_is_not_duped', contents='test2')
    # What to expect?
    exp_duped_files = [  # '/phonyDir/dir1/this_file_is_duped',
        '\\phonyDir\\dir1\\this_file_is_duped2',
        '\\phonyDir\\dir1\\dir2\\this_file_is_duped4',
        '\\phonyDir\\dir2\\this_file_is_duped3',
    ]
    exp_survived_files = [
        '\\phonyDir\\dir1\\this_file_is_duped',
        '\\phonyDir\\dir1\\this_file_is_not_duped',
        '\\phonyDir\\dir1\\dir2\\this_file_is_not_duped',
        '\\phonyDir\\dir2\\this_file_is_not_duped',
    ]
    # Execute!
    (new_files, dup_files) = DupFinder.fs.FindDupFilesInDirectory('/phonyDir')
    assert exp_duped_files == dup_files
    assert exp_survived_files == new_files
    # dup_files should still be there
    for f in dup_files:
        assert os.path.isfile(f)
    # new_files should be there
    for f in new_files:
        assert os.path.isfile(f)
    (new_files, dup_files) = DupFinder.fs.FindDupFilesInDirectory('/phonyDir', True)
    assert exp_duped_files == dup_files
    assert exp_survived_files == new_files
    # dup_files should be deleted
    for f in dup_files:
        assert not os.path.isfile(f)
    # new_files should be there
    for f in new_files:
        assert os.path.isfile(f)


def test_hash_file(fs):
    """ Test to hash a file
    Cases
    -----
    - Not existing file (should return None)
    - Existing file (should return Digest)
    - None (should return None)
    - Pass directory (should return None)
    """
    # prepare file system
    fs.create_file('/phonyDir/testfile', contents='test')
    # Not existing file (should return None)
    assert DupFinder.fs.hash_file('notexisting.txt') is None
    # Existing file (should return Digest)
    assert DupFinder.fs.hash_file(
        '/phonyDir/testfile') == xxhash.xxh64('test').hexdigest()
    # None (should return None)
    assert DupFinder.fs.hash_file(None) is None
    # Pass directory (should return None)
    assert DupFinder.fs.hash_file('/phonyDir') is None
    assert DupFinder.fs.hash_file('/phonyDir/') is None


def test_fill_up_hash(fs):
    """ Fills up hash in dictionary
    Cases
    -----
    - Passing None (should raise except)
    - Passing Wrong dictionary (without 'hash' key) (should raise Except)
    - Passing Wrong dictionary (without 'filepath' key and None in 'hash') (should raise Except)
    - Passing correct dictionary with filled 'hash' (should not change it)
    - Passing correct dictionary with None in 'hash' (shold fill it)
    """
    # Passing None (should raise except)
    with pytest.raises(TypeError):
        DupFinder.fs.fill_up_hash(None)
    # Passing Wrong dictionary (without 'hash' key) (should raise Except)
    with pytest.raises(KeyError):
        inp = {'filepath': '', 'size': 42}
        DupFinder.fs.fill_up_hash(inp)
    # Passing Wrong dictionary (without 'filepath' key, and None in 'hash') (should raise Except)
    with pytest.raises(KeyError):
        inp = {'size': 42, 'hash': None}
        DupFinder.fs.fill_up_hash(inp)
    # Passing correct dictionary with filled 'hash' (should not change it)
    inp = {'filepath': 'doesnotmatter.txt',
           'size': 42, 'hash': 'DO_NOT_CHANGE'}
    DupFinder.fs.fill_up_hash(inp)
    assert inp['hash'] == 'DO_NOT_CHANGE'
    # Passing correct dictionary with None in 'hash' (shold fill it)
    # prepare file system
    fs.create_file('nowitmatters.txt', contents='test')
    inp = {'filepath': 'nowitmatters.txt',
           'size': 42, 'hash': None}
    DupFinder.fs.fill_up_hash(inp)
    assert inp['hash'] == xxhash.xxh64('test').hexdigest()


def test_fill_up_hashes(fs):
    """ Fills up hashes in list of dictionaries
    Cases
    -----
    Basically dictionary inside the list is covered by test_fill_up_hash
    test. So, this test tests only list thingy
    - passing None (should raise Except)
    - passing empty list (should return empty list)
    - passing one dict entry (should update it (or not))
    - passing two dict entries (should update it (or not))
    """
    # passing None
    with pytest.raises(TypeError):
        DupFinder.fs.fill_up_hashes(None)
    # passing empty list (should not modify anything)
    inp = []
    DupFinder.fs.fill_up_hashes(inp)
    assert inp == []
    # passing one dict entry
    fs.create_file('nowitmatters.txt', contents='test')
    inp = {'filepath': 'nowitmatters.txt',
           'size': 42, 'hash': None}
    lis = [inp]
    DupFinder.fs.fill_up_hashes(lis)
    assert lis[0]['hash'] == xxhash.xxh64('test').hexdigest()
    # passing two dict entries
    fs.create_file('nowitmatters2.txt', contents='test2')
    inp = {'filepath': 'nowitmatters.txt', 'size': 42, 'hash': None}
    inp2 = {'filepath': 'nowitmatters2.txt', 'size': 42, 'hash': None}
    lis = [inp, inp2]
    DupFinder.fs.fill_up_hashes(lis)
    assert lis[0]['hash'] == xxhash.xxh64('test').hexdigest()
    assert lis[1]['hash'] == xxhash.xxh64('test2').hexdigest()
