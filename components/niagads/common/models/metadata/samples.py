from typing import List, Optional, Union

from niagads.common.constants.ontologies import BiosampleType
from niagads.common.models.core import TransformableModel
from niagads.common.models.ontologies import OntologyTerm
from pydantic import Field


class BiosampleCharacteristics(TransformableModel):
    system: Optional[List[str]] = Field(
        default=None, title="Biosample: Anatomical System"
    )
    tissue: Optional[List[str]] = Field(default=None, title="Biosample: Tissue")
    biomarker: Optional[List[str]] = Field(default=None, title="Biomarker")
    biosample_type: Optional[Union[BiosampleType, str]] = Field(
        default=None, title="Biosample Type"
    )
    biosample: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Biosample",
        description="ontology term/id pairs describing the biosample",
    )

    life_stage: Optional[str] = Field(
        default=None,
        title="Biosample: Life Stage",
        description="donor or sample life stage",
    )

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = {
            k: (
                self._list_to_string(v, delimiter=delimiter)
                if isinstance(v, list) and k != "biosample"
                else v
            )
            for k, v in super()._flat_dump(null_free=nullFree).items()
        }
        if self.biosample is not None:
            # have to redo b/c its been serialized above
            obj["biosample"] = self._list_to_string(self.biosample, delimiter=delimiter)

        return obj
