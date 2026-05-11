from typing import Any, List, Self, Union
from niagads.genome_reference.human import HumanGenome
from niagads.utils.dict import info_string_to_dict
from niagads.utils.string import to_json
from pydantic import BaseModel
from cyvcf2 import Variant

VCF_HEADER_FIELDS = [
    "chrom",
    "pos",
    "id",
    "ref",
    "alt",
    "qual",
    "filter",
    "info",
    "format",
]


class VCFEntry(BaseModel):
    chrom: str
    pos: int
    id: str
    ref: str
    alt: Union[list, str] = "."  # for structural variants
    qual: str = "."
    filter: str = "."
    info: Union[dict, str] = "."
    format: str = "."

    @staticmethod
    def format_dict(obj: dict, skip: List[str] = []):
        for key, value in obj.items():
            if key in skip:
                continue
            elif key == "alt":
                if "," in value:
                    obj[key] = value.split(",")
                else:
                    obj[key] = [value]
            elif value is None:
                obj[key] = "."
            elif isinstance(value, str):
                obj[key] = to_json(value)

        return obj

    @staticmethod
    def cyvcf2_info2dict(info: Any):
        if info is None or info == ".":
            return "."
        return VCFEntry.format_dict(dict(info))

    @classmethod
    def from_line(cls, entry: str) -> Self:
        entryObj = VCFEntry.format_dict(
            dict(zip(VCF_HEADER_FIELDS, entry.strip().split("\t"))), skip=["info"]
        )
        if entryObj["info"] != ".":
            entryObj["info"] = info_string_to_dict(entryObj["info"])

        return cls(**entryObj)

    @classmethod
    def from_cyvcf2_variant(cls, variant: Variant, alt_allele: str = None) -> Self:
        """Create VCFEntry from a cyvcf2 Variant object.

        Args:
            variant: cyvcf2 Variant object to parse.
            alt_allele: Optional specific ALT allele to extract. If provided,
                validates that it exists in the variant's ALT alleles.

        Returns:
            VCFEntry with single ALT allele (if alt_allele specified) or
            the full ALT list from the variant.

        Raises:
            ValueError: If alt_allele is provided but not found in variant.ALT.
        """
        if alt_allele is not None:
            if not variant.ALT.includes(alt_allele):
                raise ValueError(
                    f"Can not parse VCFEntry -> invalid alt allele: {alt_allele}; {variant}"
                )
        return cls(
            chrom=variant.CHROM,
            pos=variant.POS,
            id=variant.ID or ".",
            ref=variant.REF,
            alt=alt_allele or variant.ALT or ".",
            qual=str(variant.QUAL) if variant.QUAL is not None else ".",
            filter=variant.FILTER or ".",
            info=(
                cls.cyvcf2_info2dict(variant.INFO) if hasattr(variant, "INFO") else "."
            ),
            format=".",  # FIXME: appears sometimes empty list, sometimes bool when not present at all
        )
