from typing import Any, List, Self, Union
from niagads.assembly.core import Human
from niagads.utils.dict import info_string_to_dict
from niagads.utils.string import to_json
from pydantic import BaseModel, ConfigDict
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
            if value is None:
                obj[key] = "."
            if isinstance(value, str):
                obj[key] = to_json(value)

        return obj

    @staticmethod
    def cyvcf2_info2dict(info: Any):
        if info is None:
            return info
        return VCFEntry.format_dict(dict(info))

    @classmethod
    def from_pysam_entry(cls, entry: str) -> Self:
        entryObj = VCFEntry.format_dict(
            dict(zip(VCF_HEADER_FIELDS, entry.split("\t"))), skip=["info"]
        )
        if entryObj["info"] != ".":
            entryObj["info"] = info_string_to_dict(entryObj["info"])

        return cls(**entryObj)

    @classmethod
    def from_cyvcf2_variant(cls, variant: Variant) -> Self:
        return cls(
            chrom=str(Human(str(variant.CHROM))),
            pos=variant.POS,
            id=variant.ID or ".",
            ref=variant.REF,
            alt=",".join(variant.ALT) or ".",
            qual=str(variant.QUAL) if variant.QUAL is not None else ".",
            filter=variant.FILTER or ".",
            info=(
                cls.cyvcf2_info2dict(variant.INFO) if hasattr(variant, "INFO") else "."
            ),
            format=".",  # FIXME: appears sometimes empty list, sometimes bool when not present at all
        )
