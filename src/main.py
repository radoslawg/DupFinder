import DupFinder.fs
import DupFinder.db
import argparse
import os

parser = argparse.ArgumentParser()

subparsers = parser.add_subparsers(help='', dest='command')
p = subparsers.add_parser('create_db', help='help create_db')
p.add_argument("--use_db", "-d", metavar="path_to_db")
p = subparsers.add_parser('index_dir', help='help for index_dir')
p.add_argument("--use_db", "-d", metavar="path_to_db")
p.add_argument("dir")
p = subparsers.add_parser('check_dir', help='help for check_dir')
p.add_argument("--use_db", "-d", metavar="path_to_db")
p.add_argument("--delete-dup-files", action="store_true")
p.add_argument("--add-new-files-to-index", "-a", action="store_true")
p.add_argument("dir")
p = subparsers.add_parser(
    'find_dups_in_dir', help='Find Duplicates in directory')
p.add_argument("--delete-dup-files", action="store_true")
p.add_argument("dir")
args = parser.parse_args()

db_to_use = '~/DupFinder.db'
if args.command == 'create_db':
    if args.use_db is not None or args.use_db != '':
        db_to_use = args.use_db
    DupFinder.db.create_db(db_to_use)
if args.command == 'index_dir':
    if args.use_db is not None or args.use_db != '':
        db_to_use = args.use_db
    db = DupFinder.db.connect_db(db_to_use)
    index = DupFinder.fs.index_files_in_dir(args.dir)
    print(len(index), ' files being indexed')
    DupFinder.db.add_items(db, index)
    db.close()
if args.command == 'check_dir':
    if args.use_db is not None or args.use_db != '':
        db_to_use = args.use_db
    db = DupFinder.db.connect_db(db_to_use)
    files = DupFinder.fs.index_files_in_dir(args.dir, False)
    new_files, dup_files = DupFinder.fs.compare_with_db(db, files)
    if args.delete_dup_files:
        for fi in dup_files:
            os.remove(fi['filepath'])
    if args.add_new_files_to_index:
        DupFinder.fs.fill_up_hashes(new_files)
        DupFinder.db.add_items(db, new_files)
    print(len(dup_files), ' duplicated files found')
    print(len(new_files), ' new files found')
if args.command == 'find_dups_in_dir':
    new_files, dup_files = DupFinder.fs.FindDupFilesInDirectory(args.dir,
                                                                False)
    print(dup_files)
