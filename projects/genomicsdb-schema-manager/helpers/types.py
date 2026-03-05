from niagads.enums.core import CaseInsensitiveEnum


class DBRole(CaseInsensitiveEnum):
    ETL = "etl_runner"
    APP = "app_readonly"
