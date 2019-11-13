import os
import xxhash
import DupFinder.db


def enumerate_directory(path):
    """
    This function recursively finds all files in given directory

    Parameters
    ----------
    path : string
           Starting directory from which to find all files
    Returns
    -------
           List of type ScanDir
    """
    s = os.scandir(path)
    rec = []
    for f in s:
        if f.is_file():
            rec = rec + [f]
        if f.is_dir():
            rec = rec + enumerate_directory(f.path)
    s.close()
    return rec


def hash_file(path):
    """
    Calculates hash for the file of given path

    Parameters
    ----------
    path: string
        Path to file to be hashed

    Returns
    -------
        Hash digest calculated for given file
    """
    if path is None or not os.path.isfile(path):
        return None
    fo = open(path, 'rb')
    c = fo.read()
    r = xxhash.xxh64(c).hexdigest()
    fo.close()
    return r


def conv_file_to_dict(file_obj, calcHashes=True):
    """
    Helper method that converts ScanDir object to dictionary that can be
    consumed by this application

    Parameters
    ----------
    file_obj: ScanDir object
              Pointer to file information.
    calcHashes: boolean
              If Hashes for files needs to be calculated. For optimization
              reasons that is not always desirable nor needed.

    Returns
    -------
    Dictionary consumable by this application
    """
    r = {'filepath': file_obj.path,
         'size': os.stat(file_obj.path).st_size,  # file_obj.stat().st_size,
         'hash': None}
    if calcHashes:
        r['hash'] = hash_file(file_obj.path)
    return r


def index_files_in_dir(path, calcHashes=True):
    """
    Indexes all files in directory with sub directories, returning list of
    dictionaries with file information.

    Parameters
    ----------
    path: string
          Starting path to index
    calcHashes: boolean
          If hashes need to be calculated for files. For optimization reason
          this is often not required

    Returns
    -------
    List of dictionaries with files information
    """
    files = enumerate_directory(path)
    dict_list = [conv_file_to_dict(x, calcHashes) for x in files]
    return dict_list


def compare_with_db(db, files):
    """
    Compares list of files (dictionary struct) with database and returns two
    lists of dups and non-dups files. If files suspected of being dups won't
    have hashes calculated, this method will hash them.

    Parameters
    ----------
    db : sqlite3.Connection
        Connection to database
    files: dict
        Dictionary of suspected files.

    Returns
    -------
    (new_files, dup_files)
        Tuple, where first entry is list of not recognized files and second
        entry is list of possible duplicates.
    """
    new_files = []
    dup_files = []
    for suspect in files:
        dba = DupFinder.db.get_by_size(db, suspect['size'])
        if dba is None or len(dba) == 0:
            new_files.append(suspect)
        else:
            if suspect['hash'] is None:
                suspect['hash'] = hash_file(suspect['filepath'])
            # use generator here for (ab)use of short-circuit functionality
            found_dups = (dba_dups['hash'] == suspect['hash']
                          for dba_dups in dba)
            if any(found_dups) > 0:
                dup_files.append(suspect)
            else:
                new_files.append(suspect)
    return (new_files, dup_files)


def fill_up_hashes(files):
    """ Fill up hashes in whole list
    Parameters
    ----------
    files: list
        list of dictionary entries
    """
    for suspect in files:
        fill_up_hash(suspect)


def fill_up_hash(entry):
    """ Fill up hash in dictionary
    Parameters
    ----------
    files: dictionary
        FileDup dictionary.
    """
    if entry['hash'] is None:
        entry['hash'] = hash_file(entry['filepath'])


def FindDupFilesInDirectory(directory, delete_duplicates=False):
    """ Finds Duplicated Files in given directory (recursive) and optionally deletes them.
    Parameters
    ----------
    directory: string
        Directory to start searching from
    delete_duplicates: boolean
        Whether to delete found duplicates. Defaults to True
    Returns
    -------
    (files, duplicated_files): tuple
        files - files that have no duplicates
        duplicated_files - files that are duplicated
    """
    files = index_files_in_dir(directory, False)
    dup_files = []
    new_files = []
    for (idx, f) in enumerate(files):
        if 'marked' not in f:
            new_files.append(f['filepath'])
        for i in range(idx+1, len(files)):
            if f['size'] == files[i]['size'] and 'marked' not in files[i]:
                # We have potentially duplicate here.
                fill_up_hash(f)
                fill_up_hash(files[i])
                if (f['hash'] == files[i]['hash']):
                    # We have duplicate!
                    dup_files.append(files[i]['filepath'])
                    files[i]['marked'] = True  # This has been checked already
    if delete_duplicates:
        for f in dup_files:
            os.remove(f)
    return (new_files, dup_files)
