import sqlite3
import os

INSERT_SQL = """
    INSERT INTO Dupfinder(filepath, size, hash) VALUES(:filepath, :size, :hash)
    """
INDEX_SQL = """
    CREATE INDEX SizeIndex ON Dupfinder(size)
    """
CREATE_SQL = """
    CREATE TABLE Dupfinder (filepath, size, hash)
    """
GET_BY_SIZE_SQL = """
    SELECT filepath, size, hash FROM DupFinder
    WHERE size = ?
    """


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def create_db(db_file):
    """
    Creates database file using sqlite3 backend. You can pass :memory:
    for inmemory db. If file exists, this function will return None.

    Parameters
    ----------
    db_file : string
        Full path to db file that needs to be created.

    Returns
    -------
    db
        Handle to database or None if something went wrong
        (i.e. file already exists)
    """
    if os.path.isfile(db_file):
        return None

    conn = sqlite3.connect(db_file)
    conn.row_factory = dict_factory
    if conn is None:
        return None
    c = conn.cursor()
    c.execute(CREATE_SQL)
    c.execute(INDEX_SQL)
    c.close
    return conn


def connect_db(db_file):
    """
    Connects to existing db file. It makes no sense to do it in :memory: so it
    fails by not being valid file name in isfile.
    It also registers dictionary factory to return nice dict object instead of tuples.

    Parameters
    ----------
    db_file : string
        Full path to db file that needs to be created.

    Returns
    -------
    db
        Handle to database or None if something went wrong
        (i.e. file does not exist)
    """
    if not os.path.isfile(db_file):
        return None
    conn = sqlite3.connect(db_file)
    conn.row_factory = dict_factory
    return conn


def add_item(db, item, commit=True):
    """
    Adds item to existing db connection.
    Parameters
    ----------
    db : sqlite3.Connection
         Db Connection
    item : Dictionary of values that are to be added to database

    Returns
    -------
    bool
         If item has been successfuly added to database.
    """
    if db is None or item is None:
        return False
    assert item['hash'] is not None
    assert item['hash'] != ''
    db.execute(INSERT_SQL, item)
    if commit:
        db.commit()
    return True


def add_items(db, items):
    """
    Add many items to database.
    /This could be optimized - I'm sure/
    Parameters
    ----------
    db : sqlite3.Connection
         Db Connection
    items : List of dictionaries of values that are to be added to database
    """
    for d in items:
        add_item(db, d, False)
    db.commit()


def get_by_size(db, size):
    """
    Assumingly this is the most used query for DB. It searches database for
    entries with same file size. This is the first step for comparing files.
    Parameters
    ----------
    db   : sqlite3.Connection
           Db Connection
    size : 
           Size of the file to be searched for
    Returns
    ----------
    List of dictionaries containing rows from databse.
    """
    if db is None:
        return None
    cur = db.cursor()
    cur.execute(GET_BY_SIZE_SQL, (size,))
    return cur.fetchall()
