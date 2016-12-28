from os import path
import glob
import zipfile
import os
import sys
import hashlib

def globbed_files(dir):
    "must be a glob.txt file in this dir"
    with open(path.join(dir, 'glob.txt')) as f:
        lines = f.read().splitlines()
    # add all of the globbed entries to the files set (unique)
    files = set()
    for g in lines:
        files_in_glob =  glob.glob(path.join(dir, g))
        files |= set(files_in_glob)
    return sorted(files)


def hash_zip_file(zip_file_name):
    # BUF_SIZE is totally arbitrary, change for your app!
    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
    sha1 = hashlib.sha1()
    zip = zipfile.ZipFile(zip_file_name, "r")
    for name in zip.namelist():
        data = zip.read(name)
        sha1.update(data)
    zip.close()
    return sha1.hexdigest()

def zip_file_add_comment(zip_file_name, comment):
    "add a comment to zip file"
    zip = zipfile.ZipFile(zip_file_name, "a")
    zip.comment = comment
    zip.close()

def zip_file_remove_comment(zip_file_name):
    "add a comment to zip file"
    zip = zipfile.ZipFile(zip_file_name, "a")
    zip.comment = ""
    zip.close()

def build(zip_file_name):
    'build the application and store it in zip_file_name return the hash based on the file contents (not the comment)'
    build_dir = path.dirname(path.realpath(__file__)) # my directory is the build directory
    root_dir = path.dirname(build_dir) # root contains root/build (build_dir) and root/application
    application_dir = path.join(root_dir, 'application')
    files = globbed_files(application_dir)

    zip = zipfile.ZipFile(zip_file_name, "w")
    zip.comment = ""
    for f in files:
        zip_name = path.relpath(f, application_dir)
        if path.isfile(f):
            zip.write(f, zip_name)
    zip.close()
    hash = hash_zip_file(zip_file_name)
    zip_file_add_comment(zip_file_name, "the comment")
    zip_file_remove_comment(zip_file_name)
    return hash
