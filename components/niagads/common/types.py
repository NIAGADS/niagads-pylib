from enum import auto
from typing import Annotated

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.regular_expressions import RegularExpressions
from pydantic import Field

T_PubMedID = Annotated[str, Field(pattern=RegularExpressions.PUBMED_ID)]
T_DOI = Annotated[str, Field(pattern=RegularExpressions.DOI)]
T_Gene = Annotated[str, Field(pattern=RegularExpressions.GENE)]
T_VariantID = Annotated[str, Field(pattern=RegularExpressions.POSITIONAL_VARIANT_ID)]
T_RefSNP = Annotated[str, Field(pattern=RegularExpressions.REFSNP)]


class ProcessStatus(CaseInsensitiveEnum):
    SUCCESS = auto()
    FAIL = auto()
    RUNNING = auto()


# placed here to avoid creating a dependency in the `database` component on the `etl` component
class ETLOperation(CaseInsensitiveEnum):
    """
    Type of ETL operation:
    - LOAD: Insert new or Update existing records.
    - UPDATE: Update existing records.
    - DELETE: Delete records.
    - INSERT: Insert new records.
    - SKIP: Skip a record
    """

    INSERT = auto()
    UPDATE = auto()
    LOAD = auto()
    DELETE = auto()
    SKIP = auto()


    def past_tense(self):
        if self == ETLOperation.SKIP:
            return "SKIPPED"
        
        if self.name.endswith('E'):
            return f"{self.name}D"

        return f"{self.name}ED"