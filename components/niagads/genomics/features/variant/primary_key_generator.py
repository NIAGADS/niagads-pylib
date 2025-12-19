"""
Primary key generators for GenomicsDB variant records.

Defines classes and functions to generate unique primary keys for variant records using SPDI, VRS, and related standards.
"""

import json
import logging
import hashlib
import base64
from ga4gh.core import ga4gh_identify, ga4gh_serialize, ga4gh_digest
from ga4gh.vrs.extras.translator import AlleleTranslator, _DataProxy
from ga4gh.vrs.dataproxy import create_dataproxy
from GenomicsDBData.Util.utils import warning, die, xstr, print_dict
from ga4gh.vrs.models import SequenceLocation, SequenceReference
from ga4gh.vrs.normalize import normalize


class VariantPKGenerator(object):
    """! Generator for variant record primary key.

    Keys are generated using the following specifications:
    - [NCBI dbSNP SPDI or Sequence:Position:Deletion:Insertion](https://www.ncbi.nlm.nih.gov/variation/notation/)
    - [GA4GH VRS Computed Sequence Representations](https://vrs.ga4gh.org/en/stable/impl-guide/computed_identifiers.html#computed-identifiers)
      + this has a dependency on the [BioCommons SeqRepo](https://github.com/biocommons/biocommons.seqrepo)

    According to the following rules:
    - for SNV's and short INDEX (total length alleles <= maxSequenceLength):
      + VCF S:P:D:I, with restriction that deletion (reference) length should not substituted for the sequence
      + 1-based positions
    - for large INDELS/SVs (total length alleles > maxSequenceLength)
      + S:P:VRS_CI
    - if an external id is provided (e.g., refSNP or ss) it is provided at the end so that PKs are as follows:
      + S:P:D:I:refSNP
      + S:P:VRS_CI:refSNP
    """

    def __init__(
        self,
        genomeBuild,
        seqrepoProxyPath,
        maxSequenceLength=50,
        normalize=False,
        verbose=False,
        debug=False,
    ):
        """! VariantPKGenerator base class initializer
        @param genomeBuild          Assembly name (e.g., GRCh38, GRCh37)
        @param seqrepoProxyPath     full path to the file-based seqrepo data repository / required by GA4GH VRS
        @param maxSequenceLength    max length for ref & alt alleles, above which sequence should be digested
        @param normalize            apply GA4GH normalization
        @param verbose              verbose output flag
        @param debug                debug flag

        @return                     An instance of the VariantPKGenerator class with initialized translator
        """

        self._verbose = verbose
        self._debug = debug
        self.logger: logging.Logger = logging.getLogger(__name__)
        self._genomeBuild = genomeBuild
        self._maxSequenceLength = maxSequenceLength
        self._ga4gh_sequence_map = {}
        self._alleleTranslator = None
        self._sequenceTranslator = None
        self._seqrepoDataProxy: _DataProxy = None

        self._initialize_dataproxy(seqrepoProxyPath)
        self._initialize_translators(normalize)

    def get_ga4gh_sequence_location(self, chrm, start, end, genomeBuild="GRCh38"):
        # modeled after gnomad approach
        # https://github.com/broadinstitute/gnomad-browser/blob/3acd1354137b28b311f24ba14cb77478423af0ac/graphql-api/src/graphql/resolvers/va.ts#L135
        refgetAccession = self._seqrepoDataProxy.translate_sequence_identifier(
            f"{genomeBuild}:{chrm}", "ga4gh"
        )[0].replace("ga4gh:", "")

        if self._debug:
            self.logger.debug(f"{chrm} -> refget={refgetAccession}")

        location = SequenceLocation(
            sequenceReference=SequenceReference(refgetAccession=refgetAccession),
            start=start,
            end=end,
        )
        return normalize(location)

    def generate_sv_primary_key(self, chrm: str, start, end, svType):
        # SVTYPE_CHR1_ENCODEDREGION
        location: SequenceLocation = self.get_ga4gh_sequence_location(chrm, start, end)
        # locationId = ga4gh_identify(location).replace("ga4gh:SL.", "")
        # this gives us an encoding w/hypens and dashes

        locationId = hashlib.sha512(
            json.dumps(location.model_dump()).encode("utf-8")
        ).hexdigest()

        pk = f"{svType}_{chrm.upper()}_{locationId[:8].upper()}"
        if self._debug:
            self.logger.debug(
                f"PK for {chrm}:{start}-{end} - {svType} -> {pk} / location_id = {locationId}"
            )
        return pk

    def generate_primary_key(self, metaseqId, externalId=None, requireValidation=True):
        """! generate and returns the primary key
        @param metaseqId         metaseq or SPDI formatted (with deletion sequence) variant representation
        @param externalId        refSnp or subSnp ID
        @returns                 generated primary key
        """

        chrm, position, ref, alt = metaseqId.split(":")

        pk = [chrm, position]
        longSequence = False
        if len(ref) + len(alt) <= self._maxSequenceLength:
            pk.extend([ref, alt])
        else:
            try:
                pk.append(self.compute_vrs_identifier(metaseqId, requireValidation))
            except Exception as err:
                x = str(err)
                raise ValueError(f"Sequence mismatch for {metaseqId}: {x}")

        if externalId is not None:
            pk.append(externalId)

        return ":".join(pk)

    def get_vrs_allele_dict(
        self, metaseqId, serialize=False, toJson=False, requireValidation=True
    ):
        """! get the GA4GH VRS Allele dict, given a variant
        @param metaseqId          metaseq or SPDI formatted (with deletion sequence) variant representation
        @param serialize          serialize to binary object
        @param toJson             return as JSON object

        @returns                  VRS Allele dict in format specified by flags
        """

        # transform metaseq id to gnomad id (replace ':' with '-')
        # using gnomad b/c it accepts chrNum instead of refseq accession (required by SPDI)
        gnomadExpr = metaseqId.replace(":", "-")
        alleleDict = self._translator._from_gnomad(
            gnomadExpr,
            assembly_name=self._genomeBuild,
            require_validation=requireValidation,
        )

        if serialize:
            return ga4gh_serialize(alleleDict)
        if toJson:
            return alleleDict.for_json()

        return alleleDict

    def compute_vrs_identifier(self, metaseqId, requireValidation=True):
        """! return computed GA4GH identifier for the variant
        @param metaseqId          metaseq or SPDI formatted (with deletion sequence) variant representation
        @returns                  VRS Computed Identifier with ga4gh:VA prefix removed
        """

        try:
            alleleDict = self.get_vrs_allele_dict(metaseqId, requireValidation)

            if self._debug:
                debugOutput = {
                    "Input Variant": metaseqId,
                    "VRS Representation": alleleDict.for_json(),
                }
                warning(print_dict(debugOutput, pretty=True))

            vrsComputedId = ga4gh_identify(alleleDict)
            return vrsComputedId.split(".")[1]
        except Exception as err:
            raise err
