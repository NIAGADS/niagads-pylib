from ga4gh.vrs.models import Allele
from niagads.common.variant.models.record import VariantRecord as BaseVariantRecord
from pydantic import Field


class GA4GHVariantRecord(BaseVariantRecord):
    """Variant Record w/added ga4gh_vrs field"""

    ga4gh_vrs: Allele = Field(title="GA4GH VRS")
