from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches


class VariantNomenclature(CaseInsensitiveEnum):
    HGVS = "hgvs"
    SPDI = "spdi"
    BEACON = "beacon"
    GNOMAD = "gnomad"
    POSITIONAL = "positional"

    def regexp_map(self):
        match self.name:
            case "HGVS":
                return RegularExpressions.HGVS
            case "SPDI":
                return RegularExpressions.SPDI
            case "BEACON":
                return RegularExpressions.BEACON_VARIANT_ID
            case "GNOMAD":
                return RegularExpressions.GNOMAD_VARIANT_ID
            case "POSITIONAL":
                return RegularExpressions.POSITIONAL_VARIANT_ID
            case _:
                raise ValueError(f"Unknown variant nomenclature: {self.name}")

    def is_valid(self, variant_id: str, fail_on_error: bool = False) -> bool:
        is_valid = matches(self.regexp_map(), variant_id)
        if not is_valid and fail_on_error:
            raise ValueError(f"Invalid '{self.name}' variant: {variant_id}.")
        else:
            return is_valid

    @classmethod
    def convert_positional_to_gnomad(cls, variant_id: str):
        if cls.POSITIONAL.is_valid(variant_id):
            return variant_id.replace(":", "-")
        else:
            raise ValueError(
                f"Cannot convert: '{variant_id}' is not a valid 'POSITIONAL' variant identifier."
            )

    @classmethod
    def convert_gnomad_to_positional(cls, variant_id: str):
        if cls.GNOMAD.is_valid(variant_id):
            return variant_id.replace("-", ":")
        else:
            raise ValueError(
                f"Cannot convert: '{variant_id}' is not a valid 'GNOMAD' variant identifier."
            )
