from typing import Any, Self, Union
from niagads.genome.core import Human
from niagads.utils.string import to_json, to_number
from pydantic import BaseModel, ConfigDict
from cyvcf2 import Variant

VCF_HEADER_FIELDS = [
    "CHROM",
    "POS",
    "ID",
    "REF",
    "ALT",
    "QUAL",
    "FILTER",
    "INFO",
    "FORMAT",
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
    def cyvcf2_info2dict(info: Any):
        if info is None:
            return info

        infoObj = dict(info)
        for key, value in infoObj.items():
            if value is None:
                infoObj[key] = "."
            if isinstance(value, str):
                infoObj[key] = to_json(value)

        return infoObj

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
