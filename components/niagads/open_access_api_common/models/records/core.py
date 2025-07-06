from niagads.enums.core import CaseInsensitiveEnum


class Entity(CaseInsensitiveEnum):
    GENE = "gene"
    VARIANT = "variant"
    SPAN = "span"
    TRACK = "track"

    def __str__(self):
        return self.value.title()
