from sys import stdout
from copy import deepcopy
from typing import Type
from . import Record, RecordParser
from .. import VariantConsequenceTypes, FileFormats, Databases

from niagads.utils.string import xstr, dict_to_info_string
from niagads.utils.dict import get, print_dict
from niagads.utils.exceptions import RestrictedValueError


## variant record  parsers
class VariantRecordParser(RecordParser):
    def __init__(self, database, record=None, debug=False):
        super().__init__(database, record, debug)
        self._annotation = None
        if record is not None:
            self.set_record(record)  # handle error checking

    def has_annotation_field(self):
        return self._annotation is not None

    def set_record(self, record):
        super().set_record(record)
        self._annotation = self._record.get("annotation", None)

    def get_annotation_types(self):
        if self.has_annotation_field():
            return list(self._annotation.keys())
        else:
            raise AttributeError(
                "Record has no annotation field or annotation is NoneType"
            )


# end class


class GenomicsVariantRecordParser(VariantRecordParser):
    def __init__(self, database, record=None):
        super().__init__(database, record)

    def get_allele_frequencies(self, sources=[], asString=False):
        """get allele frequencies; if asString = True then return as // delimited list
        info strings reporting the freq for each population in a datasource

        Args:
            sources (string list, optional): list of sources to retrieve. Defaults to []; returns all populations.
                --e.g., gnomAD, 1000Genomes
        Returns:
            frequency object or
            a string that uses // to delimitate an info string for each data source
            info strings are semi-colon delimited population=freq pairs
        """
        alleleFreqs = get(self._annotation, "allele_frequencies", None, "ignore")
        if alleleFreqs is None:
            return None
        else:
            # note no way to validate sources b/c not all sources will be in all annotations
            # unless we store a reference array of valid sources
            sKeys = (
                list(alleleFreqs.keys())
                if len(sources) == 0 or sources is None
                else sources
            )
            freqs = [] if asString else {}
            for source, populations in alleleFreqs.items():
                if source not in sKeys:
                    continue

                if asString:
                    sFreqs = "source=" + source + ";" + dict_to_info_string(populations)
                    freqs = freqs + [sFreqs]
                else:
                    freqs[source] = populations

            if len(freqs) == 0:
                return None

            return "//".join(freqs) if asString else deepcopy(freqs)

    def get_associations(self, genomeWideOnly=False, asString=False):
        """extract association (GWAS summary statistics resuls)
        from a variant annotations

        Args:
            asString (bool, optional): flag indicating whether or not to return info string. Defaults to False.
            genomeWideOnly (bool, optional): flag indicating whether to return genome wide assocs only

        Returns:
            if asString is False
                associations object
            else:
                info string of dataset=pvalue pairs delimited by semicolons
        """
        associations = get(self._annotation, "associations")
        if associations is not None:
            if asString:
                if genomeWideOnly:
                    return dict_to_info_string(
                        {
                            key: value["p_value"]
                            for key, value in associations.items()
                            if value["is_gws"] == 1
                        }
                    )
                else:
                    return dict_to_info_string(
                        {key: value["p_value"] for key, value in associations.items()}
                    )
            else:
                if genomeWideOnly:
                    return {
                        key: value
                        for key, value in associations.items()
                        if value["is_gws"] == 1
                    }
                else:
                    return deepcopy(associations)

    def get_consequences(self, conseqType, asString=False):

        try:
            cType = VariantConsequenceTypes[conseqType.upper()].value
        except KeyError as err:
            raise RestrictedValueError(
                "variant consequence type", conseqType.upper(), VariantConsequenceTypes
            )
            # raise ValueError("Invalid variant consequence type: " + conseqType
            #     + "; valid values are " + xstr(VariantConsequenceTypes.list()))

        try:
            conseqAnnotations = None
            rankedConsequences = None
            if cType == "most_severe_consequence":
                conseqAnnotations = get(self._annotation, cType)
            else:
                rankedConsequences = get(
                    self._annotation, VariantConsequenceTypes.ALL.value
                )
                if rankedConsequences is not None:
                    conseqAnnotations = get(rankedConsequences, cType, None, "ignore")

            if cType == "ranked_consequences":
                return (
                    print_dict(rankedConsequences) if asString else rankedConsequences
                )

            if conseqAnnotations and asString:
                conseqArray = []
                for c in conseqAnnotations:
                    conseq = deepcopy(c)  # b/c we are going to modify part
                    conseq["consequence_terms"] = ",".join(conseq["consequence_terms"])
                    conseqArray += [dict_to_info_string(conseq)]
                return "//".join(conseqArray)
            else:
                return conseqAnnotations

        except KeyError as err:
            if cType == "ranked_consequences":
                raise RuntimeError(
                    "`ranked_consequences` missing from API response; did you specify returning a full report?"
                )
            else:
                raise err


class VariantRecord(Record):
    def __init__(self, database, requestUrl="https://api.niagads.org", variantIds=None):
        super().__init__("variant", database, requestUrl, variantIds)
        self.__full = False  # retrieve full annotation?
        self.__query_variants = None
        if variantIds is not None:
            self.set_ids(variantIds)  # initializes query_variants

    def retrieve_full_annotation(self, flag=True):
        """
        retrieve full annotation? if set to false (default for variant lookups)
        only basic annotation: identifiers, most severe predicted consequence
        will be retrieved

        full annotation includes: ADSP QC, allele frequencies, CADD scores,
        all predicted consequences

        Args:
            flag (bool, optional): flag indicating whether to retrieve full annotation. Defaults to True.
        """
        self.__full = flag
        self.set_params({"full": flag})

    def set_ids(self, ids):
        """
        overloads parent `set_ids` to clean variant ids
        and create the user -> cleaned id mapping
        """

        self.__query_variants = self.__parse_variant_ids(ids)
        self._ids = list(self.__query_variants.keys())

    def __clean_variant_id(self, id):
        """
        clean variant ids
            -- remove 'chr'
            -- replace 'MT' with 'M'
            -- replace 'RS' with 'rs'
            -- replace '/' with ':' (e.g., chr:pos:ref/alt)
            -- replace '_' with ':' (e.g., chr:pos:ref_alt)

        Args:
            id (string): variant identifier (expects rsId or chr:pos:ref:alt)

        Returns:
            string list of cleaned variant identifiers
        """
        return (
            id.replace("chr", "")
            .replace("MT", "M")
            .replace("RS", "rs")
            .replace("/", ":")
            .replace("_", ":")
        )

    def __parse_variant_ids(self, variantIds):
        """
        create mapping of user supplied variant id : cleaned id for lookups

        Args:
            queryVariants (string list): list of variants

        Returns:
            dict : cleaned id -> id mapping
        """
        return {self.__clean_variant_id(id): id for id in variantIds}

    def run(self):
        params = {} if self._params is None else self._params
        if self.__full is not None:
            self.set_params(params | {"full": self.__full})
        super().run()

    def build_parser(self):
        if self._database == Databases.GENOMICS:
            return GenomicsVariantRecordParser(self._database)
        else:
            return VariantRecordParser(self._database)

    def write_response(self, file=stdout, format=None):
        if format is None:
            format = self._response_format
        if format.upper() == FileFormats.JSON:
            return super().write_response(file, format)
        else:
            return self.__write_tabular_response(file)

    def __write_tabular_response(self, file):
        if self._database == Databases.GENOMICS:
            self.__write_genomics_tabular_response(file, self.build_parser())
        else:
            raise NotImplementedError(
                "Writing tabular output not yet implemented for "
                + self._database
                + " variant records."
            )

    def __build_10k_freq_array(self, freqs):
        if freqs is None:
            return [None * 6]
        else:
            pops = ["afr", "amr", "eas", "eur", "sas", "gmaf"]
            freqs = freqs["1000Genomes"]
            return [freqs[p] if p in freqs else None for p in pops]

    # note use of Type hints here, allows linter to autocomplete
    # also allows autoDocstring to fill in the types for the params
    def __write_genomics_tabular_response(
        self, file, parser: Type[GenomicsVariantRecordParser]
    ):
        """write a tabular report about a GenomicsDB variant lookup

        Args:
            file (str | pipe): output file name; may be stdout
            parser (Type[GenomicsVariantRecordParser]): record parser
        """
        header = [
            "queried_variant",
            "mapped_variant",
            "ref_snp_id",
            "is_adsp_variant",
            "most_severe_consequence",
            "msc_impacted_gene_id",
            "msc_impacted_gene_symbol",
            "msc_annotations",
        ]

        header = header + [
            "CADD_phred_score",
            "associations",
            "num_associations",
            "num_sig_assocations",
        ]

        header = header + [
            "1000Genomes_AFR",
            "1000Genomes_AMR",
            "1000Genomes_EAS",
            "1000Genomes_EUR",
            "1000Genomes_SAS",
            "1000Genomes_GMAF",
            "other_allele_frequencies",
        ]

        if self.__full:
            header = header + [
                "transcript_consequences",
                "regulatory_feature_consequences",
                "motif_feature_consequences",
            ]

        print("\t".join(header), file=file)

        resultJson = self.get_response()
        for variant in resultJson:
            parser.set_record(variant)

            values = [
                self.__query_variants[parser.get("queried_variant")],
                parser.get("metaseq_id"),
                parser.get("ref_snp_id"),
                parser.get("is_adsp_variant"),
            ]

            msConseq = parser.get_consequences("most_severe")
            if msConseq is not None:
                terms = ",".join(msConseq.get("consequence_terms", None))
                del msConseq["consequence_terms"]
                geneInfo = [None, None]
                if "gene_id" in msConseq:
                    geneInfo[0] = msConseq["gene_id"]
                    del msConseq["gene_id"]
                if "gene_symbol" in msConseq:
                    geneInfo[1] = msConseq["gene_symbol"]
                    del msConseq["gene_symbol"]
                values = values + [terms] + geneInfo + [dict_to_info_string(msConseq)]
            else:
                values = values + [None, None, None, None]

            annotation = parser.get("annotation")
            if annotation is not None:
                caddScores = get(annotation, "cadd_scores")
                values = values + [
                    caddScores["CADD_phred"] if "CADD_phred" in caddScores else None
                ]

                associations = parser.get_associations()
                if associations is not None:
                    values = values + [
                        parser.get_associations(asString=True),
                        len(associations),  # number associations
                        len(parser.get_associations(genomeWideOnly=True)),
                    ]  # number of genome wide associations
                else:
                    values = values + [None, None, None]

                # TODO: fix allele frequencies reporting

                freq10k = self.__build_10k_freq_array(
                    parser.get_allele_frequencies(sources=["1000Genomes"])
                )
                values = (
                    values + freq10k + [parser.get_allele_frequencies(asString=True)]
                )

                if self.__full:
                    values = values + [
                        parser.get_consequences("transcript", asString=True)
                    ]
                    values = values + [
                        parser.get_consequences("regulatory", asString=True)
                    ]
                    values = values + [parser.get_consequences("motif", asString=True)]

            print(
                "\t".join(
                    [xstr(v, null_str=self._nullStr, falseAsNull=True) for v in values]
                ),
                file=file,
            )


# end class
