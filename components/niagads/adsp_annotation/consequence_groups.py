"""@brief ADSP Consequence Group Enum"""

##
# @file consequence_groups.py
#
# @brief  ADSP Consequence Group Enum
#
# @section conseq_group_enum Description
# Defines an Enum class to store & manipulate groups of consequence terms
# to facilitate the ranking of VEP variants according to ADSP criteria
#
# @section todo_conseq_group_enum TODO
#
# @section author_conseq_group_enum Author(s)
# - Created by Emily Greenfest-Allen (fossilfriend) 2022


# pylint: disable=line-too-long,invalid-name,no-self-use
from enum import Enum
from niagads.list_utils.core import list_to_indexed_dict, is_subset, is_overlapping_list


class ConseqGroup(Enum):
    """Enum class to store & manipulate groups of consequence terms
    to facilitate the ranking of VEP variants according to ADSP criteria

    > NOTE: 'HIGH' IMPACT group also includes consequences classified by VEP as 'MODERATE' or 'LOW'

    - terms added by EGA:
        + regulatory_region_ablation 02/14/2022
        + TFBS_amplification 02/15/2022
        + regulatory_region_amplification 02/22/2022
    """

    __order__ = "HIGH_IMPACT NMD NON_CODING_TRANSCRIPT MODIFIER"
    HIGH_IMPACT = [
        "transcript_ablation",
        "splice_acceptor_variant",
        "splice_donor_variant",
        "stop_gained",
        "frameshift_variant",
        "stop_lost",
        "start_lost",
        "inframe_insertion",
        "inframe_deletion",
        "missense_variant",
        "protein_altering_variant",
        "splice_region_variant",
        "incomplete_terminal_codon_variant",
        "stop_retained_variant",
        "start_retained_variant",
        "synonymous_variant",
        "coding_sequence_variant",
        "5_prime_UTR_variant",
        "3_prime_UTR_variant",
        "regulatory_region_ablation",
    ]  # GRP 4

    NMD = ["NMD_transcript_variant"]  # GRP 1

    NON_CODING_TRANSCRIPT = [
        "non_coding_transcript_exon_variant",
        "non_coding_transcript_variant",
    ]  # GRP 2

    MODIFIER = [
        "intron_variant",
        "mature_miRNA_variant",
        "non_coding_transcript_variant",
        "non_coding_transcript_exon_variant",
        "upstream_gene_variant",
        "downstream_gene_variant",
        "TF_binding_site_variant",
        "TFBS_ablation",
        "TFBS_amplification",
        "TF_binding_site_variant",
        "regulatory_region_amplification",
        "regulatory_region_variant",
        "intergenic_variant",
    ]  # GRP 3

    @classmethod
    def get_all_terms(cls):
        """retrieve complete set of terms across all consequence groups

        ~~~~~~~~~~~~~{.py}
        ConseqGroups.get_all_terms() #usage
        ~~~~~~~~~~~~~

        @returns complete set of terms across all consequence groups
        """
        terms = []
        for x in ConseqGroup:
            if (
                x.name != "NON_CODING_TRANSCRIPT"
            ):  # subset of MODIFIER & want to preserve order
                terms += x.value

        return terms

    @classmethod
    def get_complete_indexed_dict(cls):
        """return indexed OrderedDict containing all ConseqGroup terms

        ~~~~~~~~~~~~~{.py}
        ConseqGroups.get_complete_indexed_dict() #usage
        ~~~~~~~~~~~~~

        @returns complete set of terms as ordered dict of key:value = term:index
        """
        values = ConseqGroup.get_all_terms()
        return list_to_indexed_dict(values)

    @classmethod
    def validate_terms(cls, conseqs):
        """verify that all terms fall into a conseq group
        raise error if novel term is found so that code can be updated to assign to a specific
        consequence group

        - see [Ensembl VEP Consequences](https://useast.ensembl.org/info/genome/variation/prediction/predicted_data.html)
        for possible updates

        ~~~~~~~~~~~~~{.py}
        ConseqGroup.validate_terms(conseqs) # usage
        ~~~~~~~~~~~~~

        @returns True if all terms are valid
        """

        validTerms = ConseqGroup.get_all_terms()

        for c in conseqs:
            if not is_subset(c.split(","), validTerms):
                for term in c.split(","):  # determine which specific term failed
                    if term not in validTerms:
                        raise IndexError(
                            "Consequence combination `"
                            + c
                            + "` contains an invalid consequence: `"
                            + term
                            + "`. Please update the `ConseqGroup` enum "
                            + "(conseq_group_enum.py) after reviewing "
                            + "https://useast.ensembl.org/info/genome/variation/prediction/predicted_data.html"
                        )

        return True

    def __str__(self):
        """convert enum value to comma separated string

        ~~~~~~~~~~~~~{.py}
        str(ConseqGroup.HIGH_IMPACT) # usage
        ~~~~~~~~~~~~~

        @returns comma separated string of enum values
        """
        return ",".join(self.value)

    def get_group_members(self, conseqs, requireSubset=True):
        """given a list of combinations, extracts those that
          include group members following ADSP Annotation rules

          - MODIFIER: conseqs are a subset of enum values
          - NMD, NON_CODING_TRANSCRIPT: conseqs include enum values
          - HIGH_IMPACT: conseqs include HIGH_IMPACT values, but not NMD or NON_CODING_TRANSCRIPT values

        ~~~~~~~~~~~~~{.py}
        ConseqGroup.MODIFIER.get_members(conseqs) # usage
        ~~~~~~~~~~~~~

        @returns list of conseqs that include terms belonging to the enum group
        """

        ConseqGroup.validate_terms(conseqs)

        if (
            requireSubset
        ):  # all terms must be in this group for a consequence to be a member
            return [x for x in conseqs if is_subset(x.split(","), self.value)]

        else:
            if (
                self.name == "HIGH_IMPACT"
            ):  # need to ignore consequence combos that include NMD/non-coding
                return [
                    x
                    for x in conseqs
                    if is_overlapping_list(x.split(","), self.value)
                    and not is_overlapping_list(
                        x.split(","), ConseqGroup.NON_CODING_TRANSCRIPT.value
                    )
                    and not is_overlapping_list(x.split(","), ConseqGroup.NMD.value)
                ]
            else:
                return [
                    x for x in conseqs if is_overlapping_list(x.split(","), self.value)
                ]

    def toDict(self):
        """transform enum values into indexed OrderedDict

        ~~~~~~~~~~~~~{.py}
        ConseqGroups.MODIFIER.toDict() #usage
        ~~~~~~~~~~~~~

        @returns OrderedDict key:value = term:index
        """
        return list_to_indexed_dict(self.value)
