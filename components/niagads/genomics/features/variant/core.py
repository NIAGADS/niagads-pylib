"""variant annotator functions"""

from niagads.genomics.sequence.utils import reverse_complement
from niagads.utils.string import truncate, xstr


class VariantAnnotator(object):
    """
    Functions used to generate variant annotations.
    """

    def __init__(self, refAllele, altAllele, chrom, position):
        self.__ref = refAllele
        self.__alt = altAllele
        self.__chrom = chrom
        self.__position = position
        self.__metaseqId = None
        self.__set_metaseq_id()

    @staticmethod
    def __truncate_allele(value, long=False):
        """
        Truncate an allele string for display.

        Args:
            value (str): Allele string.
            long (bool): If True, truncate to 100 chars; else 8 chars.

        Returns:
            str: Truncated allele string.
        """
        return truncate(value, 100) if long else truncate(value, 8)

    def infer_variant_end_location(self):
        """
        Infer the end location of a variant (span of indels/deletions).

        Returns:
            int: End location of the variant.
        """

        ref = self.__ref
        alt = self.__alt

        normRef, normAlt = self.get_normalized_alleles()

        rLength = len(ref)
        aLength = len(alt)

        nrLength = len(normRef)
        naLength = len(normAlt)

        position = int(self.__position)

        if rLength == 1 and aLength == 1:  # SNV
            return position

        if rLength == aLength:  # MNV
            if ref == alt[::-1]:  # inversion
                return position + rLength - 1

            # substitution
            return position + nrLength - 1

        if naLength >= 1:  # insertion
            if nrLength >= 1:  # indel
                return position + nrLength
            # e.g. CCTTAAT/CCTTAATC -> -/C but the VCF position is at the start and not where the ins actually happens
            elif nrLength == 0 and rLength > 1:
                return position + rLength - 1  # drop first base
            else:
                return position + 1

        # deletion
        if nrLength == 0:
            return position + rLength - 1
        else:
            return position + nrLength

    def __normalize_alleles(self, snvDivMinus=False):
        """
        Left normalize VCF alleles by removing leftmost matching bases.

        Args:
            snvDivMinus (bool): Return '-' for SNV deletion when True, else empty string.

        Returns:
            tuple: Normalized (ref, alt) alleles.
        """

        rLength = len(self.__ref)
        aLength = len(self.__alt)

        if rLength == 1 and aLength == 1:  # SNV no normalization needed
            return self.__ref, self.__alt

        lastMatchingIndex = -1
        for i in range(rLength):
            r = self.__ref[i : i + 1]
            a = self.__alt[i : i + 1]
            if r == a:
                lastMatchingIndex = i
            else:
                break

        if lastMatchingIndex >= 0:
            normAlt = self.__alt[lastMatchingIndex + 1 : len(self.__alt)]
            if not normAlt and snvDivMinus:
                normAlt = "-"

            normRef = self.__ref[lastMatchingIndex + 1 : len(self.__ref)]
            if not normRef and snvDivMinus:
                normRef = "-"

            return normRef, normAlt

        # MNV no normalization needed
        return self.__ref, self.__alt

    def __set_metaseq_id(self):
        """
        Generate and set the metaseq ID for the variant.
        """
        self.__metaseqId = ":".join(
            (xstr(self.__chrom), xstr(self.__position), self.__ref, self.__alt)
        )

    def get_metaseq_id(self):
        """
        Get the metaseq ID for the variant.

        Returns:
            str: Metaseq ID.
        """
        return self.__metaseqId

    def get_sv_display_attributes(self, svType: str):
        pass

    def get_display_attributes(self, rsPosition=None):
        """
        Generate and return display alleles and dbSNP-compatible start-end.

        Args:
            rsPosition (int, optional): dbSNP property RSPOS.

        Returns:
            dict: Display attributes for the variant.
        """

        LONG = True

        position = self.__position

        refLength = len(self.__ref)
        altLength = len(self.__alt)

        normRef, normAlt = self.__normalize_alleles()  # accurate length version
        nRefLength = len(normRef)
        nAltLength = len(normAlt)
        normRef, normAlt = self.__normalize_alleles(
            True
        )  # display version (- for empty string)

        endLocation = self.infer_variant_end_location()

        attributes = {"location_start": position, "location_end": position}

        normalizedMetaseqId = ":".join(
            (xstr(self.__chrom), xstr(self.__position), normRef, normAlt)
        )
        if normalizedMetaseqId != self.__metaseqId:
            attributes.update({"normalized_metaseq_id": normalizedMetaseqId})

        if refLength == 1 and altLength == 1:  # SNV
            attributes.update(
                {
                    "variant_class": "single nucleotide variant",
                    "variant_class_abbrev": "SNV",
                    "display_allele": self.__ref + ">" + self.__alt,
                    "sequence_allele": self.__ref + "/" + self.__alt,
                }
            )

        elif refLength == altLength:  # MNV
            # inversion
            if self.__ref == reverse_complement(self.__alt):
                attributes.update(
                    {
                        "variant_class": "inversion",
                        "variant_class_abbrev": "MNV",
                        "display_allele": "inv" + self.__ref,
                        "sequence_allele": self.__truncate_allele(self.__ref)
                        + "/"
                        + self.__truncate_allele(self.__alt),
                        "location_end": endLocation,
                    }
                )
            else:
                attributes.update(
                    {
                        "variant_class": "substitution",
                        "variant_class_abbrev": "MNV",
                        "display_allele": normRef + ">" + normAlt,
                        "sequence_allele": self.__truncate_allele(normRef)
                        + "/"
                        + self.__truncate_allele(normAlt),
                        "location_start": position,
                        "location_end": endLocation,
                    }
                )
        # end MNV

        elif nAltLength >= 1:  # insertion
            attributes.update({"location_start": position + 1})

            insPrefix = "ins"

            # check for duplication (whole string, not subset)
            originalRef = self.__ref[1:]  # strip first base (since it is start - 1)
            nDuplications = originalRef.count(normAlt)
            if originalRef == normAlt or (
                nDuplications > 0 and len(originalRef) / nDuplications == len(normAlt)
            ):
                insPrefix = "dup"

            if nRefLength >= 1:  # indel
                attributes.update(
                    {
                        "location_end": endLocation,
                        "display_allele": "del"
                        + self.__truncate_allele(normRef, LONG)
                        + insPrefix
                        + self.__truncate_allele(normAlt, LONG),
                        "sequence_allele": self.__truncate_allele(normRef)
                        + "/"
                        + self.__truncate_allele(normAlt),
                        "variant_class": "indel",
                        "variant_class_abbrev": "INDEL",
                    }
                )

            # indel b/c insertion location is downstream of position
            elif nRefLength == 0 and endLocation != position + 1:
                attributes.update(
                    {
                        "location_end": endLocation,
                        "display_allele": "del"
                        + self.__truncate_allele(originalRef, LONG)
                        + insPrefix
                        + self.__truncate_allele(normAlt, LONG),
                        "sequence_allele": self.__truncate_allele(normRef)
                        + "/"
                        + self.__truncate_allele(normAlt),
                        "variant_class": "indel",
                        "variant_class_abbrev": "INDEL",
                    }
                )

            else:  # just insertion
                attributes.update(
                    {
                        "location_end": position + 1,
                        "display_allele": insPrefix
                        + self.__truncate_allele(normAlt, LONG),
                        "sequence_allele": insPrefix + self.__truncate_allele(normAlt),
                        "variant_class": (
                            "duplication" if insPrefix == "dup" else "insertion"
                        ),
                        "variant_class_abbrev": insPrefix.upper(),
                    }
                )

        else:  # deletion
            attributes.update(
                {
                    "variant_class": "deletion",
                    "variant_class_abbrev": "DEL",
                    "location_end": endLocation,
                    "location_start": position + 1,
                    "display_allele": "del" + self.__truncate_allele(normRef, LONG),
                    "sequence_allele": self.__truncate_allele(normRef) + "/-",
                }
            )

        return attributes
