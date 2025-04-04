"""! @brief ADSP VEP Consequence Parser and Ranker"""

##
# @package parsers
# @file adsp_consequence_parser.py
#
# @brief  ADSP VEP Consequence Parser and Ranker
# 
# @section adsp_consequence_parser Description
# Some python functions for ranking consequence combinations
#
# modifed by EGA/fossilfriend (2021-2022) as follows:
#  - wrap in class
#  - moved file/load parsing & consequence matching / fetching from vep_parser.py
#  - added save option
#  - removed unnecessary string parsing which accounts for by JSON & parsing UTF-8 encoding on file reads
#  - replace original code dependency on pandas w/set operations & OrderedDict
#  - introduced ConseqGroup enum to facilitate ranking
#  - introduced readable variable names to follow conventions of GenomicsDB coding
#  - NOTE: to improve readability adopted the following conventions
#    + `terms`: a single consequence combination of one or more terms; in list format
#    + `conseq`: a single consequence combination, in comma separated string form
#    + `conseqs`: a list of consequence combinations
#
# @section todo_adsp_consequence_parser TODO
#
# - none
#
# @section libraries_adsp_consequence_parser Libraries/Modules
# - csv: csv file reading and writing
# - collections: container datatypes (e.g., OrderedDict)
# - datetime: for putting timestamps on updates to consequence ranking file
# - [GenomicsDBData.Util.utils](https://github.com/NIAGADS/GenomicsDBData/blob/master/Util/lib/python/utils.py)
#   + provides variety of wrappers for standard file, string, list, and logging operations
# - [GenomicsDBData.Util.list_utils](https://github.com/NIAGADS/GenomicsDBData/blob/master/Util/lib/python/list_utils.py)
#   + provides variety of wrappers for set and list operations
# - [AnnotatedVDB.Util.enums](https://github.com/NIAGADS/AnnotatedVDB/tree/master/Util/lib/python/enums)
#   + enum listing groupings of consequence terms required to determine ADSP rankings
#
# @section author_adsp_consequence_parser Author(s)
# - Created by Emily Greenfest-Allen (fossilfriend) 2021-2022
# - Modified from code by Nick Wheeler, Case Western (W. Bush Group)

# pylint: disable=line-too-long,invalid-name,no-self-use
import csv
import logging
from collections import OrderedDict
from datetime import date

from niagads.sys.core import warning, die, verify_path
from niagads.string.core import to_numeric, int_to_alpha, xstr
from niagads.dict.core import print_dict
from niagads.list.core import is_equivalent_list, qw, alphabetize_string_list, list_to_indexed_dict

from .consequence_groups import ConseqGroup

class VEPConsequenceParser(object):
    """! Parser for reading and re-ranking ADSP ranked consequences of VEP output """

    def __init__(self, rankingFileName, saveOnAddConseq=False, rankOnLoad=False, verbose=False, debug=False):
        """! ConsequenceParser base class initializer

        @param rankingFileName           file containing initial consequence ranks, or newline delim list of consequences
        @param saveOnAddConseq           flag to save new version of the file after adding a new consequence
        @param rankOnLoad                flag to re-rank consequences when loading file
        @param verbose                   flag for verbose output
        @param debug                     flag for debug output

        @returns                         An instance of the ConsequenceParser class with loaded consequence rankings
        """
        self._verbose = verbose
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        self.__rankingFileName = rankingFileName
        self.__consequenceRankings = self.__parse_ranking_file()
        self.__addedConsequences = []
        self.__saveOnAddConsequence = saveOnAddConseq
        
        if rankOnLoad: # re-rank file on load (e.g., first time using a ranking file)
            if self._verbose:
                warning("INFO:", "rankOnLoad = True")
            self.__update_rankings()
            
        self._matchedConseqTerms = {} # for already matched/to speed up lookups


    def save_ranking_file(self, fileName=None):
        """! save ranking if file
        @param fileName   output file name; if no file name is provided, will upate original file name with current date 
        """

        header = qw('consequence rank')
        version = "_v" + xstr(self.get_new_conseq_count())
        if fileName is None:
            fileName = self.__rankingFileName.split('.')[0] + "_" \
                + date.today().strftime("%m-%d-%Y") + ".txt"

        if verify_path(fileName): # file already exists / add versioning for each newly added conseq
            fileName = fileName.split('.')[0] + version  + ".txt"

        with open(fileName, 'w') as ofh:
            print('\t'.join(header), file=ofh)
            for conseq, rank in self.__consequenceRankings.items():
                print(conseq, rank, sep='\t', file=ofh)
            

    def __parse_ranking_file(self):
        """! parse ranking file & save as dict 
        @returns dictionary of conseqs:rank
        """
        
        if self._verbose:
            warning("Parsing ranking file: ", self.__rankingFileName)

        result = OrderedDict()
        rank = 1
        with open(self.__rankingFileName, 'r') as fh:
            reader = csv.DictReader(fh, delimiter='\t')
            for row in reader:
                conseq = alphabetize_string_list(row['consequence']) # ensures unique keys
                if 'rank' in row:
                    result[conseq] = to_numeric(row['rank'])
                else: # assume load order is rank order
                    result[conseq] = rank
                    rank = rank + 1

                
        return result


    # =========== accessors ==================

    def get_new_conseq_count(self):    
        """! retrieve count of newly added consequences
        @returns count of newly added consequences"""
        return len(self.__addedConsequences)
    

    def new_consequences_added(self):
        """! check if new consequences were added
        @returns True if new consequences were added"""
        return len(self.__addedConsequences) > 0

    
    def get_added_consequences(self, mostRecent=False):
        """! retrieve list of newly added consequences
        @return list of new consequences"""
        return self.__addedConsequences[-1] if mostRecent else self.__addedConsequences
        
        
    def get_rankings(self):
        """! retrieve consequence rankings
        @return OrderedDict of conseqs:rank """
        return self.__consequenceRankings


    def get_consequence_rank(self, conseq, failOnError=False):
        """! retrieve value from consequence rank map for the specified consequence
        @param conseq       the consequence combination to look up
        @param failOnError  flag indicating whether to raise an error if consequence is not found
        @return return value from consequence rank map for the specified or None if not found
        """
        if conseq in self.__consequenceRankings:
            return self.__consequenceRankings[conseq]
        else:
            if failOnError:
                raise IndexError('Consequence ' + conseq + ' not found in ADSP rankings.')
            return None
        

    def find_matching_consequence(self, terms, failOnMissing=False):
        """! match list of consequences against those in the
        rankings and return ranking info associated with match

        attempt to integrate into the rankings if not found """
        
        if len(terms) == 1:
            return self.get_consequence_rank(terms[0])

        conseqKey = '.'.join(terms)
        # storing matches b/c this step is slow (checking equivalent lists etc)
        if conseqKey not in self._matchedConseqTerms:
            match = None
            for conseqStr in self.__consequenceRankings:
                conseqList = conseqStr.split(',')
                if is_equivalent_list(terms, conseqList):
                    match = self.get_consequence_rank(conseqStr)
                    break
                
            if match is None:
                # no match found
                if failOnMissing:
                    raise IndexError('Consequence combination ' + ','.join(terms) + ' not found in ADSP rankings.')
                else: # add term & make recursive cal
                    if self._verbose:
                        warning('Consequence combination ' + ','.join(terms) + ' not found in ADSP rankings.')
                    self.__update_rankings(terms)
                    return self.find_matching_consequence(terms)
                
            self._matchedConseqTerms[conseqKey] = match

        return self._matchedConseqTerms[conseqKey]

        
    # =========== reranking functions  ==================

    def get_known_consequences(self):
        """! extract the known consequences/combos 
            replaces `ret_sort_combos`

            returns as set to try and prevent duplicates

            b/c these are keys to a hash, they are unique
        """
        return list(self.__consequenceRankings.keys()) # convert from odict_keys object


    def __add_consequence(self, terms):
        """! add new consequence (combination) to the list of known consequences """

        # extract list of known consequences & add the new one
        referenceConseqs = self.get_known_consequences()
        conseqStr = alphabetize_string_list(terms)
        
        if conseqStr in referenceConseqs:
            raise IndexError('Attempted to add consequence combination ' \
                                + conseqStr + ', but already in ADSP rankings.')
        
        referenceConseqs.append(conseqStr)
        self.__addedConsequences.append(conseqStr)

        return referenceConseqs

        
    def __update_rankings(self, terms=None):
        """! update rankings, adding in new term combination if specified,
        where terms is a list of one or more consequences
        get
        ranks are applied according to the following logic:

        1. Split all consequence combos into 4 groups:
           - GRP1 - nmd: contains `NMD_transcript_variant` - ConseqGroup.NMD
           - GRP2 - nct: contains `non_coding_transcript_variant` - ConseqGroup.NON_CODING_TRANSCRIPT
           - GRP3 - low: contains ONLY consequences in ConseqGroup.MODIFIER
           - GRP4 - high: includes at least one ConseqGroup.HIGH_IMPACT / should not overlap with groups 1&2

        2. Process GRPS in descending order

        NOTE: iterating over the ConseqGroup enum will allow processing of GRPS in expected order

        TODO: fill in documentation from notes from N. Wheeler

        """

        if self._verbose:
            warning("Updating consequence rankings")
            
        conseqs = self.__add_consequence(terms) if terms is not None else self.get_known_consequences()

        sortedConseqs = []
        for grp in ConseqGroup:
            if self._debug:
                warning("Ranking", grp.name, "consequences.")
            requireSubset = True if grp.name == 'MODIFIER' else False
            members = grp.get_group_members(conseqs, requireSubset) # extract conseqs belonging to current group
            if self._debug:
                warning("Found " + str(len(members)) + ":", members)
            if len(members) > 0:
                sortedConseqs += self.__sort_consequences(members, grp)
                
        # convert to dict & update
        if self._debug:
            warning("FINAL SORTED CONSEQUENCES", sortedConseqs)
            
        self.__consequenceRankings = list_to_indexed_dict(sortedConseqs)

        if terms is not None and self.__saveOnAddConsequence:
            if self._verbose:
                warning("Added new consequence `" + ','.join(terms) + "`. Saving version:", self.get_new_conseq_count())
            self.save_ranking_file()

            
    def __sort_consequences(self, conseqs, conseqGrp):
        """! 
        sort an input list of consequence terms (a consequence combination) according 
        to a numerially indexed dictionary of their rankings
        
        dictionary of their rankings based on the 
        conseqGrp (type ConseqGroup enum) toDict()`

        returns a list of consequence terms sorted as follows:
        
        """

        # if MODIFIER (GRP 3) use MODIFIER,
        # else use HIGH_IMPACT
        # ranking dicts are retrieved here so that the calculation
        
        grpRankingDict = ConseqGroup.HIGH_IMPACT.toDict() \
          if conseqGrp.name != 'MODIFIER' \
          else conseqGrp.toDict()

        completeRankingDict = ConseqGroup.get_complete_indexed_dict() # needed for non-exclusive grps
        if self._debug:
            warning("GRP Dict:", print_dict(grpRankingDict, pretty=True))

        indexedConseqs = []
        for c in conseqs:
            indexedConseqs.append(self.__calculate_ranking_indexes(c, grpRankingDict, completeRankingDict))

        if self._debug:
            warning("Indexed", conseqGrp.name, "consequences:", indexedConseqs)

        sortedConseqs = indexedConseqs
        sortedConseqs.sort(key=lambda x: x[0]) # sorts normally by alphabetical order            
        sortedConseqs.sort(key=lambda x:len(x[0]), reverse=True) # sorts by descending length
        sortedConseqs.sort(key=lambda x: x[0][0])# sorts by first character

        if self._debug:
            warning("Sorted", conseqGrp.name, "consequences:", sortedConseqs)

        return [','.join(sc[1]) for sc in sortedConseqs] # (alpha index, term) tuples; return term as str


    def __calculate_ranking_indexes(self, conseq, grpDict, refDict):
        """!  return tuple of alphabetic representation, internally sorted consequence combo as a list)

        given a set of input consequences 
        and a numerically indexed dictionary of their ranking based on grp and reference dict
        for non-group members
    
        the alphabetic representation allows to rank on order & sum of term ranks

        modified from N. Wheeler's code as follows:
        * if terms are not present in the ranking dict in the original code,
          they are alphabetized & appended to the ranking dict, with new indexes
          --> here, a ranking dictionary containing all terms is passed for evaluating
          sets with non-exclusive group membership, and the alphabetized non-member terms
          are ranked according that dict
        """

        terms = conseq.split(',')
        if self._debug:
            warning(terms)
        memberTerms = [c for c in terms if c in grpDict]
        nonMemberTerms = [c for c in terms if c not in grpDict]
        if self._debug:
            warning("member terms:", memberTerms)
            warning("nonmember terms:", nonMemberTerms)
            
        indexes = self.__get_consequence_rank_list(memberTerms, grpDict)
        if len(nonMemberTerms) > 0:
            indexes += self.__get_consequence_rank_list(nonMemberTerms, refDict)

        if self._debug:
            warning("indexes:", indexes)
            
        # get alphabetic representation
        alphaIndexes = [int_to_alpha(x) for x in indexes]
        if self._debug:
            warning("alpha representation:", alphaIndexes)
        alphaIndexes.sort()

        # sort consequences in the combination by their ranking indexes
    
        indexedConseq = self.__internal_consequence_sort(memberTerms + nonMemberTerms, indexes, returnStr=False)
        if self._debug:
            warning("indexed", indexedConseq)
            
        return (''.join(alphaIndexes), indexedConseq)


    def __internal_consequence_sort(self, terms, rankings, returnStr = False):
        """! sort a consequence list by a list of rankings
        rankings are based on ConseqGroup indexes / hence 'internal'
        if returnStr = true, return comma separated string, else return sorted list
        """
        rankingDict = dict(zip(terms, rankings))
        sortedDict =  OrderedDict(sorted(rankingDict.items(), key=lambda kv: kv[1])) # sort by values
        if returnStr:
            return ','.join(list(sortedDict.keys()))
        else:
            return list(sortedDict.keys())
    

    def __get_consequence_rank_list(self, terms, rankingDict):
        """!
        retrieve a list of consequence rankings for each term in 
        the consequence combination according to a numerially indexed 
        dictionary of consequences in the assigned group

        # XXX: all terms should be in the rankingDict by this time / errors should
        # have been caught when list of consequences was split into groups
        """
        return [rankingDict[c] for c in terms]
