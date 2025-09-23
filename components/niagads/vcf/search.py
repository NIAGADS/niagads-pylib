from typing import List, Union
from cyvcf2 import VCF
import pysam

# from concurrent.futures import ThreadPoolExecutor, as_completed

from niagads.assembly.core import Human
from niagads.vcf.core import VCFEntry


def file_search(
    vcfFile: str,
    chrm: Union[Human, int, str],
    start: int,
    end: int,
    countsOnly: bool = False,
) -> Union[int, List[VCFEntry]]:
    """
    Search a single VCF (compressed) file for records in a given genomic region using cyvcf2

    Args:
        vcfFile (str): full path to .vcf.gz file
        chrm (Human): human chromosome
        start (int): range start
        end (int): range end

    Returns:
        matching records from the vcf as a List of VCFEntry objects

    Note: no try block b/c error handling will depend on application
    """

    region = f"{str(chrm) if isinstance(chrm, Human) else str(Human(str(chrm)))}:{start}-{end}"

    hits = []
    vcf = VCF(vcfFile)
    if countsOnly:
        return sum(1 for _ in vcf(region))

    for record in vcf(region):
        hits.append(VCFEntry.from_cyvcf2_variant(record))

    vcf.close()

    return hits


def remote_file_search(
    url, chrm: Union[Human, int, str], start: int, end: int, countsOnly: bool = False
) -> Union[int, List[VCFEntry]]:
    """
    Search a single (remote) VCF (compressed) file for records in a given genomic region using pysam

    Args:
        url (str): .vcf.gz URL
        chrm (Human): human chromosome
        start (int): range start
        end (int): range end

    Returns:
        matching records from the vcf as a List of VCFEntry objects
    """

    hits = []
    region = f"{str(chrm) if isinstance(chrm, Human) else str(Human(str(chrm)))}:{start}-{end}"
    with pysam.TabixFile(url) as vcf:
        if countsOnly:
            return sum(1 for _ in vcf.fetch(region=region))
        for entry in vcf.fetch(region=region):
            hits.append(VCFEntry.from_pysam_entry(entry))

    return hits
