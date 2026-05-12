from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime, timezone
from dateutil.parser import parse as parse_datetime


class RefSNPMergeRecord(BaseModel):
    merged_into: str
    merge_build: int = Field(alias="revision")
    merge_date: str

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("merge_date", mode="before")
    def format_date(cls, value: str):
        return (
            parse_datetime(value)
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
        )

    @classmethod
    def __prefix_ref_snp_id(cls, rsid: str):
        if rsid.startswith("rs"):
            return rsid
        else:
            return f"rs{rsid}"

    @field_validator("merged_into", mode="before")
    def prefix_merged_into(cls, value: str):
        return cls.__prefix_ref_snp_id(value)
