"""@brief VEP JSON Output Parser"""

##
# @file vep_json.py
#
# @brief  VEP JSON Output Parser
#
# @section vep_parser Description
# utils for parsing and manipulating the JSON output of [Ensembl's Variant
# Effect Predictor (VEP) software](https://useast.ensembl.org/info/docs/tools/vep/index.html)
#
# @section todo_vep_parser TODO
#
# - clean vep result to remove info that has been extracted
#
# @section author_vep_parser Author(s)
# - Created by Emily Greenfest-Allen (fossilfriend) 2019
# - Modified to remove consequence ranking to the ConsequenceParser class by EGA 2022

# pylint: disable=line-too-long,invalid-name,no-self-use

import logging

from operator import itemgetter
from copy import deepcopy

from niagads.utils.string import xstr
from niagads.utils.list import qw
from niagads.objects.core import AutoVivificationDict
from niagads.adsp_annotation.core import VEPConsequenceParser as ConsequenceParser

CONSEQUENCE_TYPES = qw("transcript regulatory_feature motif_feature intergenic")
CODING_CONSEQUENCES = qw(
    "synonymous_variant missense_variant inframe_insertion inframe_deletion stop_gained stop_lost stop_retained_variant start_lost frameshift_variant coding_sequence_variant"
)


def is_coding_consequence(conseqs):
    """check term against list of coding consequences and return
    True if found"""
    terms = conseqs.split(",") if isinstance(conseqs, str) else conseqs

    matches = [value for value in terms if value in CODING_CONSEQUENCES]

    return len(matches) > 0


class VEPJSONParser(object):
    """class to organize utils for parsing VEP JSON output"""

    def __init__(
        self, rankingFileName, rankConsequencesOnLoad=False, verbose=False, debug=False
    ):
        self._debug = debug
        self._verbose = verbose
        self.logger = logging.getLogger(__name__)

        self.__consequenceParser = ConsequenceParser(
            rankingFileName, rankOnLoad=rankConsequencesOnLoad, verbose=verbose
        )
        self.__annotation = None
        self.__rankedConsequences = {}

    def __find_matching_term(self, terms):
        """wrapper for ConsequenceParser.find_matching_consequence
        so that we can log new consequences when found

        @param terms             list of terms in the consequence combination
        @returns rank
        """
        try:
            return self.__consequenceParser.find_matching_consequence(
                terms, failOnMissing=True
            )
        except IndexError as err:
            return self.__consequenceParser.find_matching_consequence(terms)

    def assign_adsp_consequence_rank(self, conseqDict):
        """find and return rank and coding status for a consequence combination

        @param conseqDict     dict (from VEP output) containing consequence that needs to be ranked
        @returns updated conseqDict w/rank and is_coding flag
        """

        terms = conseqDict["consequence_terms"]
        conseq = ",".join(terms)
        if conseq not in self.__rankedConsequences:
            value = {
                "rank": self.__find_matching_term(terms),
                "consequence_is_coding": is_coding_consequence(terms),
            }
            self.__rankedConsequences[conseq] = value

        conseqDict.update(self.__rankedConsequences[conseq])

        return conseqDict

    def __verify_annotation(self):
        """check that annotation is set"""
        assert (
            self.__annotation is not None
        ), "DEBUG - must set value of _annotation in the VEP parser to access it"

    def adsp_rank_and_sort_consequences(self):
        """applies ADSP ranking to consequence, re orders the array and
        and saves newly ordered list
        """
        for ctype in CONSEQUENCE_TYPES:
            rankedConseqs = self.__adsp_rank_consequences(ctype)
            if rankedConseqs is not None:
                self.set(ctype + "_consequences", rankedConseqs)

    # =========== modifiers ==================
    def set_annotation(self, annotation):
        """set the annotation json"""
        self.__annotation = annotation

    def set(self, key, value):
        """set a value to annotation json"""
        self.__verify_annotation()
        self.__annotation[key] = value

    # =========== accessors ==================

    def get_added_conseq_summary(self):
        """@returns summary of added consequences from the consequence parser"""
        summary = "No new consequences added"
        if self.__consequenceParser.new_consequences_added():
            summary = " ".join(
                (
                    "Added",
                    xstr(self.__consequenceParser.get_new_conseq_count()),
                    "new consequences:",
                    "["
                    + "; ".join(self.__consequenceParser.get_added_consequences())
                    + "]",
                )
            )
        return summary

    def get_conseq_rank(self, conseq):
        """@returns value from consequence rank map for the specified
        consequence"""
        return self.__consequenceParser.get_consequence_rank(conseq)

    def get_consequence_parser(self):
        return self.__consequenceParser

    def __adsp_rank_consequences(self, conseqType):
        """extract consequences and apply ranking and sort,
        convert from list to list of dicts, keyed on allele
        to ensure consequences are sorted per allele
        @param conseqType         one of CONSEQUENCE_TYPES
        @returns ranked consequences
        """

        result = None
        consequences = self.get(conseqType + "_consequences")
        if consequences is None:
            return None

        result = {}
        for index, conseq in enumerate(consequences):
            # need to build the hash pulling the key out of variant allele &
            # appending to the list
            va = conseq["variant_allele"]
            conseq["vep_consequence_order_num"] = index

            if va in result:
                result[va].append(self.assign_adsp_consequence_rank(conseq))
            else:
                result[va] = [self.assign_adsp_consequence_rank(conseq)]

        for va in result:  # sort by rank within each variant allele
            # result[va] = sorted(result[va], key = lambda x: (x['rank'], x['vep_consequence_order_num']))
            # itemgetter supposed to be orders of magnitude faster than lambda
            result[va] = sorted(
                result[va], key=itemgetter("rank", "vep_consequence_order_num")
            )

        return result

    def get_frequencies(self, matchingVariantId=None):
        """extract frequencies from colocated_variants section
        for dbSNP VEP run -- sometimes VEP matches to variants with
        rsId different from current rsId; use matchingVariantId to ensure
        extracting the correct frequency (e.g. overlapping indels & snvs)
        """
        self.__verify_annotation()
        if "colocated_variants" not in self.__annotation:
            return None

        frequencies = None
        cv = self.__annotation["colocated_variants"]

        if len(cv) > 1:
            # return first non-cosmic mutation that matches the expected variant id (if supplied)
            fCount = 0
            for covar in cv:
                if covar["allele_string"] != "COSMIC_MUTATION":
                    if "frequencies" in covar:
                        if matchingVariantId is not None:
                            if covar["id"] == matchingVariantId:
                                frequencies = self.__extract_frequencies(covar)
                        else:
                            frequencies = self.__extract_frequencies(covar)
                            fCount = fCount + 1
            if fCount > 1:
                # based on experience, when this happens, involves multiple refsnps mapped to location,
                # so all frequencies should be equal
                # let's just print a warning
                inputVariant = self.__annotation["input"]["id"]
                if self._verbose:
                    self.logger.warn(
                        "Variant "
                        + inputVariant
                        + " mapped to multiple refSNPs/frequencies based on location not alleles"
                    )
            # else:
            return frequencies  # which may be None

        elif "frequencies" in cv[0]:
            frequencies = self.__extract_frequencies(cv[0])

        return frequencies

    def __extract_frequencies(self, covar):
        """extract frequencies and update minor allele to include
        1000 Genomes global allele frequency if present (stored in
        colocated_variant field not frequencies array)
        """

        frequencies = {}
        if "minor_allele" in covar:
            frequencies["minor_allele"] = covar["minor_allele"]
            if "minor_allele_freq" in covar:
                frequencies["minor_allele_freq"] = covar["minor_allele_freq"]

        frequencies["values"] = self.__group_frequencies_by_source(covar["frequencies"])
        return frequencies

    def __group_frequencies_by_source(self, frequencies):
        """group 1000Genomes and gnomAD frequencies"""

        if frequencies is None:
            return None

        result = AutoVivificationDict()  # needed to later add in minor allele freqs
        espKeys = ["aa", "ea"]
        for allele in frequencies:
            gnomad = {
                key: value
                for key, value in frequencies[allele].items()
                if "gnomad" in key
            }
            esp = {
                key: value
                for key, value in frequencies[allele].items()
                if key in espKeys
            }
            genomes = {
                key: value
                for key, value in frequencies[allele].items()
                if "gnomad" not in key and key not in espKeys
            }
            if bool(gnomad):
                result[allele]["GnomAD"] = gnomad
            if bool(genomes):
                result[allele]["1000Genomes"] = genomes
            if bool(esp):
                result[allele]["ESP"] = esp

        return result

    def __get_consequences(self, key):
        """special getter for consequences b/c fields may be missing; don't want
        to throw error"""
        if key in self.__annotation:
            return self.__annotation[key]
        else:
            return None

    def get(self, key):
        """get the annotation value associated with the key"""
        self.__verify_annotation()

        if key == "frequencies":
            return self.get_frequencies()
        if "consequences" in key:
            return self.__get_consequences(key)
        else:
            return self.__annotation[key]

    def get_annotation(self, deepCopy=False):
        """return updated annotation"""
        return deepcopy(self.__annotation) if deepCopy else self.__annotation

    def __get_allele_consequences(self, allele, ctypeKey):
        """get consequences of specified type for the allele, performs None checks
        @param allele                    the allele to be matched
        @param ctypeKey                  consequence type key (a CONSEQUENCE_TYPE + '_consequences'
        @returns dict of all consequences of the specified type for the specified allele
        """

        conseqs = self.get(ctypeKey)
        if conseqs is None:
            return None

        if allele in conseqs:
            return conseqs[allele]

        return None  # allele not in conseqs

    def get_allele_consequences(self, allele, conseqType=None):
        """get dict of consequences for the specified allele
        if called after ADSP ranking has been done, then retrieved
        consequences will be ADSP ranked

        @param allele                   allele to be matched
        @param conseqType               consequence type (from CONSEQUENCE_TYPES) / if None, iterate over all types
        @returns dict of consequences matched to the allele
        """
        if conseqType is None:  # get all conseqs / return nested dict
            alleleConseqs = {}
            for ctype in CONSEQUENCE_TYPES:
                ctypeKey = ctype + "_consequences"
                conseqs = self.get(ctypeKey)
                if conseqs is not None and allele in conseqs:
                    alleleConseqs[ctypeKey] = conseqs[allele]

            return None if len(alleleConseqs) == 0 else alleleConseqs

        else:
            ctypeKey = conseqType + "_consequences"
            conseqs = self.get(ctypeKey)
            return (
                conseqs[allele] if conseqs is not None and allele in conseqs else None
            )

    def get_most_severe_consequence(self, allele):
        """retrieve most severe consequence from the VEP JSON Parser,
        for the specified allele; returns None if no consequences are found
        return first hit among transcript, then regulatory feature, then intergenic
        consequences.  If called after ADSP ranking and sorting is done on the result,
        the consequences will be ADSP ranked
        @param           allele to be matched
        @result          dict representation of most severe consequence
        """
        for ctype in CONSEQUENCE_TYPES:
            msConseq = self.get_allele_consequences(allele, conseqType=ctype)
            if msConseq is not None:
                return msConseq[0]

        return None
