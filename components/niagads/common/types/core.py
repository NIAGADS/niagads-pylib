from typing import Annotated

from niagads.utils.regular_expressions import RegularExpressions
from pydantic import Field


T_PubMedID = Annotated[str, Field(pattern=RegularExpressions.PUBMED_ID)]
T_DOI = Annotated[str, Field(pattern=RegularExpressions.DOI)]
