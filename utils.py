import random
import string
import os


def get_random_id(id_set):
    """
        return a string composed of 128 random characters that is not exists in `id_set`
    """
    new_id = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
    while new_id in id_set:
        new_id = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
    return new_id


# This function set the path sep to '\\' in case of windows path and '/' otherwise.
# Because most of the operating systems works with linux sep - we set the src sep to '/' by default.
def get_path(src_platform, src_path, src_sep='/'):
    if src_platform == 'win32':
        src_sep = '\\'
    if os.sep != src_sep:
        src_path = src_path.replace(src_sep, os.sep)
    return src_path


# creates the dirs by recursive in destination path
def create_dirs(d_path):
    if not os.path.exists(d_path):
        create_dirs(os.path.dirname(d_path))
        os.mkdir(d_path)


# delete dir recursively
def delete_dir(path_to_del):
    if not os.path.exists(path_to_del):
        return
    for root, dirs, files in os.walk(path_to_del, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for d in dirs:
            dir_path = os.path.join(root, d)
            os.rmdir(dir_path)
    os.rmdir(path_to_del)
