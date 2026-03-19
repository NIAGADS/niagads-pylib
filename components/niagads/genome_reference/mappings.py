import csv
from niagads.common.core import ComponentBaseMixin
from niagads.utils.string import xstr


class ChromosomeMapParser(ComponentBaseMixin):
    """Generator for chromosome map parser/object
    parses mappings of third party chromosome sequence ids (e.g., refseq) to chromosome number
    may also include chromosome length
    - for now assumes the tab-delim with at least the following columns:
    > source_id       chromosome     length
    """

    def __init__(self, fileName: str, verbose: bool = False, debug: bool = False):
        """ChromosomeMap base class initializer.
        Args:
            fileName (_type_): full path to chromosome mapping file
            verbose (bool, optional): verbose output flag. Defaults to False.
            debug (bool, optional): debug flag. Defaults to False.

        Returns:
            An instance of a ChromosomeMap with initialized mapping dict
        """
        super().__init__(debug=debug, verbose=verbose)

        self.__file = fileName
        self.__map = {}
        self.parse()

    @property
    def mapping(self):
        return self.__map

    def lookup_sequence_id(self, chrmNum):
        """Given a chromosome number, tries to find matching sequence id."""
        for sequenceId, cn in self.__map.items():
            if cn == chrmNum or cn == "chr" + xstr(chrmNum):
                return sequenceId

        return None

    def lookup_chromosome(self, sequenceId):
        """Return chromosome number mapped to the provided sequence ID."""
        # want to raise AttributeError if not in the map, so not checking
        return self.__map[sequenceId]

    def parse(self):
        """parse chromosome map"""

        if self._verbose or self._debug:
            self.logger.info("Loading chromosome map from:", self.__file)

        with open(self.__file, "r") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            for row in reader:
                # source_id	chromosome	chromosome_order_num	length
                key = row["source_id"]
                value = row["chromosome"].replace("chr", "")
                self.__map[key] = value
