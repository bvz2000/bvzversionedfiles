import hashlib
import os
import shutil

import bvzfilesystemlib


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
def copy_files_deduplicated(dest_d,
                            data_d,
                            sources_p,
                            ver_prefix="v",
                            num_digits=4,
                            do_verified_copy=False):
    """
    Given a list of source files, copy those files into the data directory and make a symlink in dest_p that points
    to these files. Does de-duplication so that if more than one file (regardless of when copied or name) contains the
    same data, it will only be stored in data_d once.

    For example:

    If dest_d is:
        /path/to/destination/directory

    and data_d is:
        /path/to/data/directory

    and sources_p is:
        {"/another/path/to/a/source/file.txt": "relative/dir/new_file_name.txt"}

    Then the file will (appear) to be copied to:
        /path/to/destination/directory/relative/dir/new_file_name.txt

    but in actual fact, the above file will be a symlink that points to:
        /path/to/data/directory/new_file_name.v001.txt

    :param dest_d:
            The full path of the root directory where the files given by sources_p will appear to be copied (they will
            appear to be copied to subdirectories of this directory, based on the relative paths given in sources_p).
            They only "appear" to be copied to these locations because in actual fact they are symlinks to the actual
            file which is copied into data_d. See the description the sources_p argument below for an example of
            how this works.
    :param data_d:
            The directory where the actual files will be stored.
    :param sources_p:
            A dictionary where the key is the path of the file to be copied, and the value is a relative path (from
            dest_d) where the file will be stored plus the destination file name.
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
    assert type(sources_p) is dict
    assert type(ver_prefix) is str
    assert type(num_digits) is int
    assert type(do_verified_copy) is bool

    if dest_d.startswith(data_d):
        raise ValueError("Destination directory may not be a child of the data directory")

    for source_p in sources_p.keys():

        if not os.path.exists(source_p):
            raise ValueError(f"CopyDeduplicated failed: source file does not exist: {source_p}")
        if not os.path.isfile(source_p):
            raise ValueError(f"CopyDeduplicated failed: source file is not a file: {source_p}")

    output = dict()

    data_sizes = bvzfilesystemlib.dir_files_keyed_by_size(data_d)
    cached_md5 = dict()  # cache each md5 checksum to avoid potentially re-doing the checksum multiple times in the loop

    for source_p, dest_relative_p in sources_p.items():

        output[source_p] = (copy_file_deduplicated(source_p=source_p,
                                                   dest_p=os.path.join(dest_d, dest_relative_p),
                                                   data_d=data_d,
                                                   data_sizes=data_sizes,
                                                   cached_md5=cached_md5,
                                                   ver_prefix=ver_prefix,
                                                   num_digits=num_digits,
                                                   do_verified_copy=do_verified_copy))

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

    # Build a relative path from dest_p to the file the file we just copied into the data dir. Then create a symlink to
    # this file in the destination.
    if os.path.exists(dest_p):
        os.unlink(dest_p)
    relative_p = os.path.join(data_file_p, dest_p)
    os.symlink(relative_p, dest_p)

    # update the data_sizes dictionary (for performance in case we are running this function inside a loop)
    bvzfilesystemlib.add_file_to_dict_by_size(source_p, data_sizes)

    return data_file_p
