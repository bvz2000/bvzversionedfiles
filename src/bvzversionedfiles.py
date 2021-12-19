import hashlib
import os
import shutil

import bvzfilesystemlib


# ------------------------------------------------------------------------------
def md5_for_file(file_p,
                 block_size=2**20):
    """
    Create an md5 checksum for a file without reading the whole file in in a
    single chunk.

    :param file_p: The path to the file we are checksumming.
    :param block_size: How much to read in in a single chunk. Defaults to 1MB

    :return: The md5 checksum.
    """

    assert os.path.exists(file_p)
    assert type(block_size) is int

    md5 = hashlib.md5()
    with open(file_p, "rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)

    return md5.digest()


# ------------------------------------------------------------------------------
def files_are_identical(file_a_p,
                        file_b_p,
                        block_size=2**20):
    """
    Compares two files to see if they are identical. First compares sizes. If
    the sizes match, then it does an md5 checksum on the files to see if they
    match. Ignores all metadata when comparing (name, creation or modification
    dates, etc.) Returns True if they match, False otherwise.

    :param file_a_p: The path to the first file we are comparing.
    :param file_b_p: The path to the second file we are comparing
    :param block_size: How much to read in in a single chunk when doing the md5
           checksum. Defaults to 1MB

    :return: True if the files match, False otherwise.
    """

    assert os.path.exists(file_a_p)
    assert os.path.isfile(file_a_p)
    assert os.path.exists(file_b_p)
    assert os.path.isfile(file_b_p)

    if os.path.getsize(file_a_p) == os.path.getsize(file_b_p):
        md5_a = md5_for_file(file_a_p, block_size)
        md5_b = md5_for_file(file_b_p, block_size)
        return md5_a == md5_b

    return False


# ------------------------------------------------------------------------------
def verified_copy_file(src,
                       dst):
    """
    Given a source file and a destination, copies the file, and then checksum's
    both files to ensure that the copy matches the source. Raises an error if
    the copied file's md5 checksum does not match the source file's md5
    checksum.

    :param src: The source file to be copied.
    :param dst: The destination file name where the file will be copied. If the
           destination file already exists, an error will be raised. You must
           supply the destination file name, not just the destination dir.

    :return: Nothing.
    """

    assert os.path.exists(src)
    assert os.path.isfile(src)
    assert os.path.exists(os.path.split(dst)[0])
    assert os.path.isdir(os.path.split(dst)[0])

    shutil.copy(src, dst)

    if not files_are_identical(src, dst):
        msg = "Verification of copy failed (md5 checksums to not match): "
        raise IOError(msg + src + " --> " + dst)


# ------------------------------------------------------------------------------
def copy_and_add_ver_num(source_p,
                         dest_d,
                         dest_n=None,
                         ver_prefix="v",
                         num_digits=4,
                         do_verified_copy=False):
    """
    Copies a source file to the dest dir, adding a version number to the file
    right before the extension. If a file with that version number already
    exists, the file being copied will have its version number incremented so as
    not to overwrite.  Returns a full path to the file that was copied.

    :param source_p: The full path to the file to copy.
    :param dest_d: The directory to copy to.
    :param dest_n: An optional name to rename the copied file to. If None, then
           the copied file will have the same name as the source file. Defaults
           to None.
    :param ver_prefix: The prefix to put onto the version number. For example,
           if the prefix is "v", then the version number will be represented as
           "v####". Defaults to "v".
    :param num_digits: How much padding to use for the version numbers. For
           example, 4 would lead to versions like: v0001 whereas 3 would lead to
           versions like: v001. Defaults to 4.
    :param do_verified_copy: If True, then a verified copy will be performed.
           Defaults to False.

    :return: A full path to the file that was copied.
    """

    assert os.path.exists(source_p)
    assert os.path.isfile(source_p)
    assert os.path.exists(dest_d)
    assert os.path.isdir(dest_d)
    assert type(num_digits) is int
    assert type(do_verified_copy) is bool

    if not dest_n:
        source_d, dest_n = os.path.split(source_p)

    base, ext = os.path.splitext(dest_n)

    v = 1
    while True:

        version = "." + ver_prefix + str(v).rjust(num_digits, "0")
        dest_p = os.path.join(dest_d, base + version + ext)

        # This is not race condition safe, but it works for most cases...
        if os.path.exists(dest_p):
            v += 1
            continue

        if do_verified_copy:
            verified_copy_file(source_p, dest_p)
        else:
            shutil.copy(source_p, dest_p)

        return dest_p


# ----------------------------------------------------------------------------------------------------------------------
def copy_files_deduplicated(sources_p,
                            dest_d,
                            data_d,
                            dest_n=None,
                            ver_prefix="v",
                            num_digits=4,
                            do_verified_copy=False):
    """
    Given a full path to a source file, copy that file into the data directory and make a symlink in dest_p that points
    to this file. Does de-duplication so that if more than one file (regardless of when copied or name) contains the
    same data, it will only be stored in data_d once.

    :param sources_p:
            The path to the source files being stored. Accepts a list of files or a single file (as a string).
    :param dest_d:
            The full path of the directory where the file will appear to be stored. In actual fact this will really
            become a symlink to the actual file which will be stored in data_d. dest_d may not be a sub-directory of
            data_d.
    :param data_d:
            The directory where the actual files will be stored.
    :param dest_n:
            An optional name to rename the copied file to. If None, then the copied file will have the same name as the
            source file. Only to be used if the passed sources_p is either a string or a list of length 1. If either of
            these is not the case, and dest_n is NOT None, an assertion error is raised. Defaults to None.
    :param ver_prefix:
            The prefix to put onto the version number used inside of the data_d dir to de-duplicate files. This version
            number is NOT added to the symlink file so, as far as the end user is concerned, the version number does not
            exist. For example, if the prefix is "v", then the version number will be represented as "v####". Defaults
            to "v".
    :param num_digits:
            How much padding to use for the version numbers. For example, 4 would lead to versions like: v0001 whereas 3
            would lead to versions like: v001. Defaults to 4.
    :param do_verified_copy:
            If True, then a verified copy will be performed. Defaults to False.

    :return:
            The string representing the path to the actual de-duplicated file in data_d. If more than one file was
            passed in as a source, then a list of paths to de-duplicated files will be returned instead.
    """

    assert not dest_d.startswith(data_d)
    assert os.path.exists(data_d)
    assert os.path.isdir(data_d)
    assert os.path.exists(dest_d)
    assert os.path.isdir(dest_d)
    assert type(num_digits) is int
    assert type(do_verified_copy) is bool
    if dest_n is not None:
        assert type(sources_p) is str or (type(sources_p) is list and len(sources_p) is 1)

    if dest_d.startswith(data_d):
        raise ValueError("Destination directory may not be a child of the data directory")

    if type(sources_p) is not list:
        sources_p = [sources_p]

    for source_p in sources_p:

        assert os.path.exists(source_p)
        assert os.path.isfile(source_p)

    output = list()

    data_sizes = bvzfilesystemlib.dir_files_keyed_by_size(data_d)
    cached_md5 = dict()

    for source_p in sources_p:

        size = os.path.getsize(source_p)

        if not dest_n:
            destination_name = os.path.split(source_p)[1]
        else:
            destination_name = dest_n

        # Check to see if there is a list of files of that size in the .data dir
        try:
            possible_matches_p = data_sizes[size]
        except KeyError:
            possible_matches_p = []

        # For each of these, try to find a matching file
        matched_p = None
        source_md5 = md5_for_file(source_p)
        for possible_match_p in possible_matches_p:
            try:
                possible_match_md5 = cached_md5[possible_match_p]
            except KeyError:
                possible_match_md5 = md5_for_file(possible_match_p)
                cached_md5[possible_match_p] = possible_match_md5
            if source_md5 == possible_match_md5:
                matched_p = possible_match_p
                break

        # If we did not find a matching file, then copy the file to the
        # data_d dir, with an added version number that ensures that we do
        # not overwrite any previous versions of files with the same name.
        if matched_p is None:
            matched_p = copy_and_add_ver_num(source_p=source_p,
                                             dest_d=data_d,
                                             dest_n=destination_name,
                                             ver_prefix=ver_prefix,
                                             num_digits=num_digits,
                                             do_verified_copy=do_verified_copy)

        os.chmod(matched_p, 0o644)

        # Build a relative path from where the symlink will go to the file in
        # the data dir. Then create a symlink to this file in the destination.
        dest_d = dest_d.rstrip(os.path.sep)
        matched_file_n = os.path.split(matched_p.rstrip(os.path.sep))[1]
        relative_d = os.path.relpath(data_d, dest_d)
        relative_p = os.path.join(relative_d, matched_file_n)
        if os.path.exists(os.path.join(dest_d, destination_name)):
            os.unlink(os.path.join(dest_d, destination_name))
        os.symlink(relative_p, os.path.join(dest_d, destination_name))

        bvzfilesystemlib.add_file_to_dict_by_size(source_p, data_sizes)

        output.append(matched_p)

    if len(output) == 1:
        return output[0]
    return output
