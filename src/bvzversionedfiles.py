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
# TODO: Make windows safe
def copy_files_deduplicated(dest_d,
                            data_d,
                            sources_p,
                            ver_prefix="v",
                            num_digits=4,
                            do_verified_copy=False):
    """
    Given a full path to a source file, copy that file into the data directory and make a symlink in dest_p that points
    to this file. Does de-duplication so that if more than one file (regardless of when copied or name) contains the
    same data, it will only be stored in data_d once.

    :param dest_d:
            The full path of the root directory where the files given by sources_p will appear to be copied (they will
            appear to be copied to subdirectories of dest_d). They only appear to be copied to subdirectories of dest_d
            because in actual fact they are copied to data_d, and a symlink to these copied files will be copied to a
            subdirectory of dest_d. dest_d may not be a subdirectory of data_d. See sources_p below for an example of
            how this works.
    :param data_d:
            The directory where the actual files will be stored.
    :param sources_p:
            A dictionary where the key is the path of the file to be copied, and the value is a relative path (from
            dest_d) where the file will be stored plus the destination file name.

            For example:

            If dest_d is:
                /path/to/destination/directory

            and data_d is:
                /path/to/data/directory

            and sources_p is:
                {"/another/path/to/a/source/file.txt": "relative/dir/new_file_name.txt"}

            Then the file will (appear) to be copied to:
                /path/to/destination/directory/relative/dir/new_file_name.txt

            (in actual fact, the above file will be a symlink that points to something similar to):
                /path/to/data/directory/new_file_name.v001.txt
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
            The string representing the path to the actual de-duplicated file in data_d. If more than one file was
            passed in as a source, then a list of paths to de-duplicated files will be returned instead.
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

    output = list()

    data_sizes = bvzfilesystemlib.dir_files_keyed_by_size(data_d)
    cached_md5 = dict()  # cache each md5 checksum to avoid potentially re-doing the checksum multiple times in the loop

    for source_p, dest_relative_p in sources_p.items():

        dest_n = os.path.split(dest_relative_p)[1]
        size = os.path.getsize(source_p)

        # Check to see if there are any files of that size in the .data dir
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
                cached_md5[possible_match_p] = possible_match_md5  # cache in case we see this file again in the loop
            if source_md5 == possible_match_md5:
                matched_p = possible_match_p
                break

        # If we did not find a matching file, then copy the file to the data_d dir, with an added version number that
        # ensures that we do not overwrite any previous versions of files with the same name.
        if matched_p is None:

            matched_p = copy_and_add_ver_num(source_p=source_p,
                                             dest_p=os.path.join(data_d, dest_n),
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
        if os.path.exists(os.path.join(dest_d, dest_n)):
            os.unlink(os.path.join(dest_d, dest_n))
        os.symlink(relative_p, os.path.join(dest_d, dest_n))

        bvzfilesystemlib.add_file_to_dict_by_size(source_p, data_sizes)

        output.append(matched_p)

    if len(output) == 1:
        return output[0]
    return output
