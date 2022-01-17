import os.path
from dataclasses import dataclass

"""
A basic class to hold the info about a single file that is to be copied using deduplication.
"""


# ======================================================================================================================
class Copydescriptor:

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 source_p,
                 dest_relative_p,
                 link_in_place=False):
        """
        Initialize the object with the data about the file to be copied.
        """

        assert type(source_p) is str
        assert type(dest_relative_p) is str
        assert type(link_in_place) is bool

        if not os.path.exists(source_p):
            raise ValueError(f"Source file {source_p} does not exist.")

        self.source_p = source_p
        self.dest_relative_p = dest_relative_p
        self.link_in_place=link_in_place
