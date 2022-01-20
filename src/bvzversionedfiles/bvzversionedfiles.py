import hashlib
import os
import shutil

import bvzfilesystemlib

from bvzversionedfiles.copydescriptor import Copydescriptor


# ----------------------------------------------------------------------------------------------------------------------
def md5_for_file(file_p,
                 block_size=2**20):
    """
    Create an md5 checksum for a file without reading the whole file in a single chunk.

    :param file_p:
            The path to the file we are check-summing.
    :param block_size:
            How much to read in a single chunk. Defaults to 1 MB

    :return:
            The md5 checksum.
    """

    assert type(file_p) is str
    assert type(block_size) is int

    md5 = hashlib.md5()
    with open(file_p, "rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)

    return md5.digest()


# ----------------------------------------------------------------------------------------------------------------------
def files_are_identical(file_a_p,
                        file_b_p,
                        block_size=2**20):
    """
    Compares two files to see if they are identical. First compares sizes. If the sizes match, then it does an md5
    checksum on the files to see if they match. Ignores all metadata when comparing (name, creation or modification
    dates, etc.) Returns True if they match, False otherwise.

    :param file_a_p:
            The path to the first file we are comparing.
    :param file_b_p:
            The path to the second file we are comparing
    :param block_size:
            How much to read in a single chunk when doing the md5 checksum. Defaults to 1 MB

    :return:
            True if the files match, False otherwise.
    """

    assert type(file_a_p) is str
    assert type(file_b_p) is str
    assert type(block_size) is int

    if os.path.getsize(file_a_p) == os.path.getsize(file_b_p):
        md5_a = md5_for_file(file_a_p, block_size)
        md5_b = md5_for_file(file_b_p, block_size)
        return md5_a == md5_b

    return False


# ----------------------------------------------------------------------------------------------------------------------
def verified_copy_file(src,
                       dst):
    """
    Given a source file and a destination, copies the file, and then checksum's both files to ensure that the copy
    matches the source. Raises an error if the copied file's md5 checksum does not match the source file's md5 checksum.

    :param src:
            The source file to be copied.
    :param dst:
            The destination file name where the file will be copied. If the destination file already exists, an error
            will be raised. You must supply the destination file name, not just the destination dir.

    :return:
            Nothing.
    """

    assert type(src) is str
    assert type(dst) is str

    shutil.copy(src, dst)

    if not files_are_identical(src, dst):
        msg = "Verification of copy failed (md5 checksums to not match): "
        raise IOError(msg + src + " --> " + dst)


# ----------------------------------------------------------------------------------------------------------------------
def copy_and_add_ver_num(source_p,
                         dest_p,
                         ver_prefix="v",
                         num_digits=4,
                         do_verified_copy=False):
    """
    Copies a source file to the dest dir, adding a version number to the file right before the extension. If a file with
    that version number already exists, the file being copied will have its version number incremented so as not to
    overwrite. Returns a full path to the file that was copied.

    :param source_p:
            The full path to the file to copy.
    :param dest_p:
            The full path to the destination file (path plus name to copy to).
    :param ver_prefix:
            The prefix to put onto the version number. For example, if the prefix is "v", then the version number will
            be represented as "v####". Defaults to "v".
    :param num_digits:
            How much padding to use for the version numbers. For example, 4 would lead to versions like: v0001 whereas 3
            would lead to versions like: v001. Defaults to 4.
    :param do_verified_copy:
            If True, then a verified copy will be performed. Defaults to False.

    :return:
            A full path to the file that was copied.
    """

    assert type(source_p) is str
    assert type(dest_p) is str
    assert type(ver_prefix) is str
    assert type(num_digits) is int
    assert type(do_verified_copy) is bool

    dest_d, dest_n = os.path.split(dest_p)
    base, ext = os.path.splitext(dest_n)

    v = 1
    while True:

        version = "." + ver_prefix + str(v).rjust(num_digits, "0")
        dest_p = os.path.join(dest_d, base + version + ext)

        if os.path.exists(dest_p):
            v += 1
            continue

        if do_verified_copy:
            verified_copy_file(source_p, dest_p)
        else:
            shutil.copy(source_p, dest_p)

        return dest_p


# ----------------------------------------------------------------------------------------------------------------------
def single_file_to_copydescriptors(file_p,
                                   relative_d,
                                   dest_n,
                                   link_in_place):
    """
    Given a full path to a file, returns a list of copydescriptors of length 1.

    :param file_p:
            A full path to the file being stored.
    :param relative_d:
            The relative path (not including the name) of where the symlinked file will live. (This is the symlink, not
            the actual file that contains data).
    :param dest_n:
            The name of the symlinked file.
    :param link_in_place:
            If True, then each file will be set to link in place.

    :return:
            A list of copydescriptor objects of length 1.
    """

    assert type(file_p) is str
    assert type(relative_d) is str
    assert type(dest_n) is str
    assert type(link_in_place) is bool

    copydescriptors = list()

    copydescriptor = Copydescriptor(source_p=file_p,
                                    dest_relative_p=os.path.join(relative_d, dest_n),
                                    link_in_place=link_in_place)
    copydescriptors.append(copydescriptor)

    return copydescriptors

# ----------------------------------------------------------------------------------------------------------------------
def file_list_to_copydescriptors(items,
                                 relative_d,
                                 link_in_place):
    """
    Given a list of files, return a list of copydescriptors.

    :param items:
            A list of files.
    :param relative_d:
            A relative path to the directory where the the symlinked files will be stored. If they are to be stored at 
            the root level, this should be set to "" or None.
    :param link_in_place:
            If True, then each file will be set to link in place.

    :return:
            A list of copydescriptor objects.
    """

    copydescriptors = list()

    if relative_d is None:
        relative_d = ""

    for item in items:
        dest_relative_p = os.path.join(relative_d, os.path.split(item)[1])
        copydescriptor = Copydescriptor(source_p=item,
                                        dest_relative_p=dest_relative_p,
                                        link_in_place=link_in_place)
        copydescriptors.append(copydescriptor)

    return copydescriptors


# ----------------------------------------------------------------------------------------------------------------------
def directory_to_copydescriptors(dir_d,
                                 link_in_place):
    """
    Given a directory, return a list of copydescriptors.

    :param dir_d:
            A directory, all children of which will be converted to copydescriptors.
    :param link_in_place:
            If True, then each file will be set to link in place.

    :return:
            A list of copydescriptor objects.
    """

    copydescriptors = list()

    for path, currentDirectory, files_n in os.walk(dir_d):
        for file_n in files_n:
            source_p = os.path.join(path, file_n)
            dest_relative_p = source_p.split(dir_d)[1]
            try:
                copydescriptor = Copydescriptor(source_p=source_p,
                                                dest_relative_p=dest_relative_p,
                                                link_in_place=link_in_place)
            except ValueError as e:
                raise SquirrelError(str(e), 5000)
            copydescriptors.append(copydescriptor)

    return copydescriptors


# ----------------------------------------------------------------------------------------------------------------------
def copy_files_deduplicated(copydescriptors,
                            dest_d,
                            data_d,
                            ver_prefix="v",
                            num_digits=4,
                            do_verified_copy=False):
    """
    Given a list of copydescriptor objects, copy the files they represent into the data directory and make a symlink in
    dest_p that points to these files. Does de-duplication so that if more than one file (regardless of when copied or
    name) contains the same data, it will only be stored in data_d once. If the copydescriptor for a file has
    link_in_place set to True, then that file will not be copied to data_d, and the symlink in dest_p will insetad point
    to the original source file.

    Example #1:

    If the copydescriptor is:
        source_p = "/another/path/to/a/source/file.txt"
        dest_relative_p = "relative/dir/new_file_name.txt"
        link_in_place = False

    and dest_d is:
        /path/to/destination/directory

    and data_d is:
        /path/to/data/directory

    Then the file will (appear) to be copied to:
        /path/to/destination/directory/relative/dir/new_file_name.txt

    but in actual fact, the above file will be a symlink that points to:
        /path/to/data/directory/new_file_name.v001.txt

    Example #2:

    If the copydescriptor is:
        source_p = "/another/path/to/a/source/file.txt"
        dest_relative_p = None
        link_in_place = True

    and dest_d is:
        /path/to/destination/directory

    Then the file will (appear) to be copied to:
        /path/to/destination/directory/relative/dir/new_file_name.txt

    but in actual fact, the above file will be a symlink that points to the original source file:
        /another/path/to/a/source/file.txt

    :param copydescriptors:
            A dictionary where the key is the path of the file to be copied, and the value is the relative path plus the
            destination file name where the file will be stored (relative from dest_d).
    :param dest_d:
            The full path of the root directory where the files given by sources_p will appear to be copied (they will
            appear to be copied to subdirectories of this directory, based on the relative paths given in the
            copydescriptor). They only "appear" to be copied to these locations because in actual fact they are symlinks
            to the actual file which is copied into data_d.
    :param data_d:
            The directory where the actual files will be stored.
    :param ver_prefix:
            The prefix to put onto the version number used inside the data_d dir to de-duplicate files. This version
            number is NOT added to the symlink file so, as far as the end user is concerned, the version number does not
            exist. For example, if the prefix is "v", then the version number will be represented as "v####". Defaults
            to "v".
    :param num_digits:
            How much padding to use for the version numbers. For example, 4 would lead to versions like: v0001 whereas 3
            would lead to versions like: v001. Defaults to 4.
    :param do_verified_copy:
            If True, then a verified copy will be performed. Defaults to False.

    :return:
            A dictionary where the key is the source file that was copied, and the value is a string representing the
            path to the actual de-duplicated file in data_d.
    """

    assert type(dest_d) is str
    assert type(data_d) is str
    assert type(copydescriptors) is list
    assert type(ver_prefix) is str
    assert type(num_digits) is int
    assert type(do_verified_copy) is bool

    if dest_d.startswith(data_d):
        raise ValueError("Destination directory may not be a child of the data directory")

    for copydescriptor in copydescriptors:

        if not os.path.exists(copydescriptor.source_p):
            raise ValueError(f"CopyDeduplicated failed: source file does not exist: {source_p}")
        if not os.path.isfile(copydescriptor.source_p):
            raise ValueError(f"CopyDeduplicated failed: source file is not a file: {source_p}")

    output = dict()

    data_sizes = bvzfilesystemlib.dir_files_keyed_by_size(data_d)
    cached_md5 = dict()  # cache each md5 checksum to avoid potentially re-doing the checksum multiple times in the loop

    for copydescriptor in copydescriptors:

        dest_p = os.path.join(dest_d, copydescriptor.dest_relative_p)

        if not copydescriptor.link_in_place:
            output[copydescriptor.source_p] = copy_file_deduplicated(source_p=copydescriptor.source_p,
                                                                     dest_p=dest_p,
                                                                     data_d=data_d,
                                                                     data_sizes=data_sizes,
                                                                     cached_md5=cached_md5,
                                                                     ver_prefix=ver_prefix,
                                                                     num_digits=num_digits,
                                                                     do_verified_copy=do_verified_copy)
        else:
            os.makedirs(os.path.split(dest_p)[0], exist_ok=True)
            if os.path.exists(dest_p):
                os.unlink(dest_p)
            os.symlink(copydescriptor.source_p, dest_p)

    return output


# TODO: Not windows compatible!!
# ----------------------------------------------------------------------------------------------------------------------
def copy_file_deduplicated(source_p,
                           dest_p,
                           data_d,
                           data_sizes,
                           cached_md5,
                           ver_prefix="v",
                           num_digits=4,
                           do_verified_copy=False):
    """
    Given a full path to a source file, copy that file into the data directory and make a symlink in dest_p that points
    to this file. Does de-duplication so that if more than one file contains the same data (regardless of name or any
    other file stats), it will only be stored in data_d once. See copy_files_deduplicated for more details.

    :param source_p:
            A full path to where the source file is.
    :param dest_p:
            The full path of where the file will appear to be copied. The file only appears to be copied to this
            location because in actual fact dest_p will be a symlink that points to the actual file which is copied to
            the directory data_d.
    :param data_d:
            The directory where the actual files will be stored.
    :param data_sizes:
            A dictionary that lists the contents of the data directory keyed by file size. The key is the size of the
            file, and the value is a list of files in the data directory that match this size.
    :param cached_md5:
            A dictionary that will be used to store cached md5 hashes to speed up the copy operation in cases where this
            function is called more than once. This may be an empty dictionary. It is populated by repeated runs of this
            function.
    :param ver_prefix:
            The prefix to put onto the version number used inside the data_d dir to de-duplicate files. This version
            number is NOT added to the symlink file so, as far as the end user is concerned, the version number does not
            exist. For example, if the prefix is "v", then the version number will be represented as "v####". Defaults
            to "v".
    :param num_digits:
            How much padding to use for the version numbers. For example, 4 would lead to versions like: v0001 whereas 3
            would lead to versions like: v001. Defaults to 4.
    :param do_verified_copy:
            If True, then a verified copy will be performed. Defaults to False.

    :return:
            The string representing the path to the actual de-duplicated file in data_d.
    """

    assert type(dest_p) is str
    assert type(data_d) is str
    assert type(source_p) is str
    assert type(ver_prefix) is str
    assert type(num_digits) is int
    assert type(do_verified_copy) is bool

    if dest_p.startswith(data_d):
        raise ValueError("Destination file may not be a child of the data directory")

    if not os.path.isfile(source_p):
        raise ValueError(f"copy_file_deduplicated failed: source file is not a file or does not exist: {source_p}")

    size = os.path.getsize(source_p)

    # Check to see if there are any files of that size in the .data dir
    try:
        possible_matches_p = data_sizes[size]
    except KeyError:
        possible_matches_p = []

    matched_p = None

    # If there are possible matches, try to find an actual match by comparing md5 checksums
    if possible_matches_p:
        source_md5 = md5_for_file(source_p)
        for possible_match_p in possible_matches_p:

            try:  # Try to get the md5 from the cached hashes first
                possible_match_md5 = cached_md5[possible_match_p]
            except KeyError:  # We don't have a cached md5 for this possible match, so create it and cache it
                possible_match_md5 = md5_for_file(possible_match_p)
                cached_md5[possible_match_p] = possible_match_md5  # cache this md5

            if source_md5 == possible_match_md5:
                matched_p = possible_match_p
                break

    # If we did not find a matching file, then copy the file to the data_d dir (this will add a version number that
    # ensures that we do not overwrite any previous versions of files with the same name).
    if matched_p is None:
        dest_n = os.path.split(dest_p)[1]
        data_file_p = copy_and_add_ver_num(source_p=source_p,
                                           dest_p=os.path.join(data_d, dest_n),
                                           ver_prefix=ver_prefix,
                                           num_digits=num_digits,
                                           do_verified_copy=do_verified_copy)
    else:
        data_file_p = matched_p

    # Create the directories where the symlink will be stored.
    os.makedirs(os.path.split(dest_p)[0], exist_ok=True)

    # Build a relative path from dest_p to the file the file we just copied into the data dir. Then create a symlink to
    # this file in the destination.
    relative_p = os.path.relpath(data_file_p, os.path.split(dest_p)[0])

    if os.path.exists(dest_p):
        os.unlink(dest_p)
    os.symlink(relative_p, dest_p)

    # update the data_sizes dictionary (for performance in case we are running this function inside a loop)
    bvzfilesystemlib.add_file_to_dict_by_size(data_file_p, data_sizes)

    return data_file_p
