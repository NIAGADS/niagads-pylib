from enum import auto
from niagads.enums.core import CaseInsensitiveEnum


class Strand(CaseInsensitiveEnum):
    SENSE = "+"
    ANTISENSE = "-"


class Assembly(CaseInsensitiveEnum):
    """enum for genome builds"""

    GRCh37 = "GRCh37"
    GRCh38 = "GRCh38"

    @classmethod
    def _missing_(cls, value: str):
        """Override super to map hg19 or hg38 to GRCh* nomenclature.
        For everything else call super() to allow case-insensitive matches"""
        if value.lower() == "hg19":
            return cls.GRCh37
        if value.lower() == "hg38":
            return cls.GRCh38
        return super(Assembly, cls)._missing_(value)

    @classmethod
    def list(cls):
        """return a list of the enum values"""
        # FIXME: need hg19, 18 for the enumparameter; check api code
        return super(Assembly, cls).list()  #  + ["hg19", "hg38"]

    def hg_label(self):
        return "hg19" if self.value == "GRCh37" else "hg38"

    # these class methods are from EnumParameters
    # no inheritence here b/c of functional programming
    # and limitations on subclassing Enums
    @classmethod
    def get_description(cls):
        return f"Allowable values are: {','.join(cls.list())}."

    @classmethod
    def validate(cls, value, label: str, returnCls: CaseInsensitiveEnum):
        from niagads.exceptions.core import ValidationError
        from niagads.api.common.utils import sanitize  # avoid circular import

        try:
            cls(sanitize(value))
            return returnCls(value)
        except Exception as err:
            raise ValidationError(
                f"Invalid value provided for `{label}`: {value}.  {cls.get_description()}"
            )
