from typing import List, Optional, Union

from niagads.common.constants.ontologies import BiosampleType
from niagads.common.models.base import TransformableModel
from niagads.common.models.ontologies import OntologyTerm
from pydantic import Field


# TODO - how to handle biosample/biosample_type pairing, should we make another model?
# impact on metadata intake?


class BiosampleCharacteristics(TransformableModel):
    biosample: List[OntologyTerm] = Field(
        default=None,
        title="Biosample",
        description="ontology term describing the biosample",
    )
    biosample_type: List[BiosampleType] = Field(
        default=None,
        title="Biosample: Type",
        description="the biological source of a sample used in an experiment",
    )
    biomarker: Optional[List[OntologyTerm]] = Field(default=None, title="Biomarker")
    system: Optional[List[str]] = Field(
        default=None,
        title="Biosample: Anatomical System",
        json_schema_extra={"is_filer_annotation": True},
    )
    tissue: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Biosample: Tissue",
        json_schema_extra={"is_filer_annotation": True},
    )

    life_stage: Optional[OntologyTerm] = Field(
        default=None,
        title="Biosample: Life Stage",
        description="donor or sample life stage",
        json_schema_extra={"is_filer_annotation": True},
    )

    def _flat_dump(self, null_free=False, delimiter="|"):
        obj = {
            k: (
                self._list_to_string(v, delimiter=delimiter)
                if isinstance(v, list) and k != "biosample"
                else v
            )
            for k, v in super()._flat_dump(null_free=null_free).items()
        }
        if self.biosample is not None:
            # have to redo b/c its been serialized above
            obj["biosample"] = self._list_to_string(self.biosample, delimiter=delimiter)

        return obj
