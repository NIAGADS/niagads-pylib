import os
from typing import Union
from cyvcf2 import VCF

# from concurrent.futures import ThreadPoolExecutor, as_completed

from niagads.genome.core import Human
from niagads.vcf.core import VCFEntry


def search_vcf_file(
    filePath: str, chrm: Union[Human, int, str], start: int, end: int, exclude=None
):
    """
    Search a single VCF (compressed) file for records in a given genomic region.

    Args:
        filePath (str): full path to .vcf.gz file
        chrm (Human): human chromosome
        start (int): range start
        end (int): range end
        exclude (string)

    Returns:
        matching records from the vcf
    """

    results = []
    try:
        # region = f"{chrm.value if isinstance(chrm, Human) else Human(str(chrm)).value}:{start}-{end}"
        region = f"{str(chrm) if isinstance(chrm, Human) else str(Human(str(chrm)))}:{start}-{end}"
        vcf = VCF(filePath)
        for record in vcf(region):
            results.append(VCFEntry.from_cyvcf2_variant(record))
            # results.append(f"{os.path.basename(filePath)}\t{str(record).strip()}")
    except Exception as e:
        raise IOError(f"Error reading VCF file: {filePath}: {e}")
    return results
