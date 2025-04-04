""" variant annotator functions """
#!pylint: disable=invalid-name
import logging
from niagads.string_utils.core import xstr, truncate, reverse

def truncate_allele(allele: str, long=False):
    """
    wrapper for trunctate alleles to 8 chars by defualt

    Args:
        allele (str): allele string
        long (bool, optional): for long indels, can specify to truncate to 100 chars. Defaults to False.

    Returns:
        truncated allele string
    """
    return truncate(allele, 100) if long else truncate(allele, 8) 


def reverse_complement(seq):
    """! @returns reverse complement of the specified sequence (seq)
    """
    mapping = str.maketrans("ACGTacgt", "TGCAtgca")
    return seq.translate(mapping)[::-1]

    
class VariantAnnotator(object):
    """ generate dervived variant annotations: e.g., normalized alleles, inferred length """

    def __init__(self, chrom: str, pos: int, ref: str, alt: str, debug=False):
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        self.__ref = ref
        self.__alt = alt
        self.__chromosome = chrom
        self.__position = pos
        self.__metaseqId = None
        self.__set_metaseq_id()


    def get_normalized_alleles(self, snvDivMinus=False):
        """! public wrapper for __normalize_alleles / LEGACY
        @returns normalized alleles """
        return self.__normalize_alleles(snvDivMinus)
    
    
    def infer_variant_end_location(self, rsPosition=None):
        """! infer span of indels/deletions for a 
        specific alternative allele, modeled off 
        GUS Perl VariantAnnotator & dbSNP normalization conventions
        @returns                 end location
        """

        ref = self.__ref
        alt = self.__alt
        
        normRef, normAlt = self.__normalize_alleles()

        rLength = len(ref)
        aLength = len(alt)
        
        nrLength = len(normRef)
        naLength = len(normAlt)

        position = int(self.__position)

        if rLength == 1 and aLength == 1: # SNV
            return position

        if rLength == aLength: # MNV
            if ref == alt[::-1]: #inversion
                return position + rLength - 1

            # substitution
            return position + nrLength - 1

        if naLength >= 1: # insertion
            if nrLength >= 1: # indel
                return position + nrLength
            # e.g. CCTTAAT/CCTTAATC -> -/C but the VCF position is at the start and not where the ins actually happens
            elif nrLength == 0 and rLength > 1: 
                return position + rLength - 1 # drop first base
            else: 
                return position + 1

        # deletion
        if nrLength == 0:
            return position + rLength - 1
        else: 
            return position + nrLength
    

    def __normalize_alleles(self, snvDivMinus=False):
        """! left normalize VCF alleles
        - remove leftmost alleles that are equivalent between the ref & alt alleles;
        e.g. CAGT/CG <-> AGT/G

        - if no normalization is possible, keeps normalized alleles as
        default equal to ref & alt

        @param snvDivMinus       return '-' for SNV deletion when True, otherwise return empty string
        @return                  a tuple containing the normalized alleles (ref, alt)
        """

        rLength = len(self.__ref)
        aLength = len(self.__alt)
        
        if rLength == 1 and aLength == 1: # SNV no normalization needed
            return self.__ref, self.__alt

        lastMatchingIndex = - 1
        for i in range(rLength):
            r = self.__ref[i:i + 1]
            a = self.__alt[i:i + 1]
            if r == a:
                lastMatchingIndex = i
            else:
                break

        if lastMatchingIndex >= 0:
            normAlt = self.__alt[lastMatchingIndex + 1:len(self.__alt)]
            if not normAlt and snvDivMinus:
                normAlt = '-'

            normRef = self.__ref[lastMatchingIndex + 1:len(self.__ref)]
            if not normRef and snvDivMinus:
                normRef = '-'

            return normRef, normAlt

        # MNV no normalization needed
        return self.__ref, self.__alt


    def __set_metaseq_id(self):
        """! generate metaseq id and set value"""
        self.__metaseqId = ':'.join((xstr(self.__chromosome), xstr(self.__position), self.__ref, self.__alt))


    def metaseq_id(self):
        """! @returns metaseq id """
        return self.__metaseqId


    def get_display_attributes(self, rsPosition = None):
        """! generate and return display alleles & dbSNP compatible start-end
        @param rsPosition       dbSNP property RSPOS
        @returns                 dict containing display attributes
        """
        
        LONG = True
        
        position = self.__position

        refLength = len(self.__ref)
        altLength = len(self.__alt)

        normRef, normAlt = self.__normalize_alleles() # accurate length version
        nRefLength = len(normRef)
        nAltLength = len(normAlt)
        normRef, normAlt = self.__normalize_alleles(True) # display version (- for empty string)
        
        endLocation = self.infer_variant_end_location()

        attributes = {
            'location_start': position,
            'location_end': position
        }
        
        normalizedMetaseqId = ':'.join((xstr(self.__chromosome), xstr(self.__position), normRef, normAlt)) 
        if normalizedMetaseqId != self.__metaseqId:
            attributes.update({'normalized_metaseq_id': normalizedMetaseqId})

        if (refLength == 1 and altLength == 1): # SNV
            attributes.update({
                'variant_class': "single nucleotide variant",
                'variant_class_abbrev': "SNV",
                'display_allele': self.__ref + '>' + self.__alt,
                'sequence_allele': self.__ref + '/' + self.__alt
            })

        elif refLength == altLength: # MNV
            #inversion
            if self.__ref == reverse(self.__alt):
                attributes.update({
                    'variant_class': "inversion",
                    'variant_class_abbrev': "MNV",
                    'display_allele': 'inv' + self.__ref,
                    'sequence_allele': truncate_allele(self.__ref) + '/' + truncate_allele(self.__alt),
                    'location_end': endLocation
                })
            else:
                attributes.update({
                    'variant_class': "substitution",
                    'variant_class_abbrev': "MNV",
                    'display_allele': normRef + ">" + normAlt,
                    'sequence_allele': truncate_allele(normRef) + '/' + truncate_allele(normAlt),
                    'location_start': position,
                    'location_end': endLocation
                })
        # end MNV
        
        elif nAltLength >= 1: # insertion
            attributes.update({'location_start': position + 1})
            
            insPrefix = "ins"   
            
            # check for duplication (whole string, not subset)      
            originalRef = self.__ref[1:] # strip first base (since it is start - 1)
            nDuplications = originalRef.count(normAlt)           
            if originalRef == normAlt or (nDuplications > 0 and len(originalRef) / nDuplications == len(normAlt)):
                insPrefix = "dup"
                
            if nRefLength >= 1: # indel
                attributes.update({
                    'location_end': endLocation,
                    'display_allele': "del" + truncate_allele(normRef, LONG) + insPrefix + truncate_allele(normAlt, LONG),
                    'sequence_allele': truncate_allele(normRef) + "/" + truncate_allele(normAlt),
                    'variant_class': 'indel',
                    'variant_class_abbrev': 'INDEL'
                    })
                
            # indel b/c insertion location is downstream of position
            elif (nRefLength == 0 and endLocation != position + 1):
                attributes.update({
                    'location_end': endLocation,
                    'display_allele': "del" + truncate_allele(originalRef, LONG) + insPrefix + truncate_allele(normAlt, LONG),
                    'sequence_allele': truncate_allele(normRef) + "/" + truncate_allele(normAlt),
                    'variant_class': 'indel',
                    'variant_class_abbrev': 'INDEL'
                    })
            
            else: # just insertion
                attributes.update({
                    'location_end': position + 1,
                    'display_allele': insPrefix + truncate_allele(normAlt, LONG),
                    'sequence_allele': insPrefix + truncate_allele(normAlt),
                    'variant_class': 'duplication' if insPrefix == 'dup' else 'insertion',
                    'variant_class_abbrev': insPrefix.upper()
                    })
                
        else: # deletion
            attributes.update({
                'variant_class': "deletion",
                'variant_class_abbrev': "DEL",      
                'location_end': endLocation,
                'location_start': position + 1,
                'display_allele': "del" + truncate_allele(normRef, LONG),
                'sequence_allele': truncate_allele(normRef) + "/-"
            })
        
        return attributes
