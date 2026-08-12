from typing import Iterator

from niagads.rdf_parsers.rdf import NTriplesParser

MESHV = "http://id.nlm.nih.gov/mesh/vocab#"


class MeSHParser(NTriplesParser):
    def __init__(
        self,
        file: str,
        logger=None,
        debug: bool = False,
        verbose: bool = False,
    ):

        super().__init__(
            file=file,
            namespace=MESHV,
            logger=logger,
            debug=debug,
            verbose=verbose,
        )

    # self._namespace.TopicalDescriptor

    def extract_topical_descriptors(self) -> Iterator[dict]:
        """q"""
        pass

    def extract_concepts(self) -> Iterator[dict]:
        pass
