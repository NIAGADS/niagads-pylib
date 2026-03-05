"""Form parsing and validation helpers for the track metadata builder."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import ValidationError
from starlette.datastructures import FormData

from niagads.api.common.models.datasets.track import Track


def _strip(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value: Optional[str]) -> Optional[int]:
    value = _strip(value)
    if value is None:
        return None
    return int(value)


def _split_lines(value: Optional[str]) -> Optional[List[str]]:
    value = _strip(value)
    if value is None:
        return None
    parsed = [line.strip() for line in value.splitlines() if line.strip()]
    return parsed or None


def _split_term_pairs(value: Optional[str]) -> Optional[List[Dict[str, str]]]:
    lines = _split_lines(value)
    if not lines:
        return None

    items = []
    for line in lines:
        if "|" in line:
            term, term_id = [x.strip() for x in line.split("|", 1)]
        else:
            term, term_id = line.strip(), None

        if not term:
            continue

        item: Dict[str, str] = {"term": term}
        if term_id:
            item["term_id"] = term_id
        items.append(item)

    return items or None


def _build_nested(raw: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "track_id": _strip(raw.get("track_id")),
        "name": _strip(raw.get("name")),
        "description": _strip(raw.get("description")),
        "genome_build": _strip(raw.get("genome_build")),
        "feature_type": _strip(raw.get("feature_type")),
        "cohorts": _split_lines(raw.get("cohorts")),
    }

    biosample_characteristics = {
        "system": _split_lines(raw.get("biosample_characteristics.system")),
        "tissue": _split_lines(raw.get("biosample_characteristics.tissue")),
        "biomarker": _split_lines(raw.get("biosample_characteristics.biomarker")),
        "biosample_type": _strip(raw.get("biosample_characteristics.biosample_type")),
        "biosample": _split_term_pairs(raw.get("biosample_characteristics.biosample")),
        "life_stage": _strip(raw.get("biosample_characteristics.life_stage")),
    }

    subject_phenotypes = {
        "disease": _split_term_pairs(raw.get("subject_phenotypes.disease")),
        "ethnicity": _split_term_pairs(raw.get("subject_phenotypes.ethnicity")),
        "race": _split_term_pairs(raw.get("subject_phenotypes.race")),
        "neuropathology": _split_term_pairs(
            raw.get("subject_phenotypes.neuropathology")
        ),
        "genotype": _split_term_pairs(raw.get("subject_phenotypes.genotype")),
        "biological_sex": _split_term_pairs(
            raw.get("subject_phenotypes.biological_sex")
        ),
    }

    experimental_design = {
        "antibody_target": _strip(raw.get("experimental_design.antibody_target")),
        "assay": _strip(raw.get("experimental_design.assay")),
        "analysis": _strip(raw.get("experimental_design.analysis")),
        "classification": _strip(raw.get("experimental_design.classification")),
        "data_category": _strip(raw.get("experimental_design.data_category")),
        "output_type": _strip(raw.get("experimental_design.output_type")),
        "is_lifted": (
            None
            if _strip(raw.get("experimental_design.is_lifted")) is None
            else _to_bool(raw.get("experimental_design.is_lifted"))
        ),
        "covariates": _split_lines(raw.get("experimental_design.covariates")),
    }

    provenance = {
        "data_source": _strip(raw.get("provenance.data_source")),
        "release_version": _strip(raw.get("provenance.release_version")),
        "release_date": _strip(raw.get("provenance.release_date")),
        "download_date": _strip(raw.get("provenance.download_date")),
        "download_url": _strip(raw.get("provenance.download_url")),
        "study": _strip(raw.get("provenance.study")),
        "project": _strip(raw.get("provenance.project")),
        "accession": _strip(raw.get("provenance.accession")),
        "pubmed_id": _split_lines(raw.get("provenance.pubmed_id")),
        "doi": _split_lines(raw.get("provenance.doi")),
        "consortium": _split_lines(raw.get("provenance.consortium")),
        "attribution": _strip(raw.get("provenance.attribution")),
    }

    file_properties = {
        "file_name": _strip(raw.get("file_properties.file_name")),
        "url": _strip(raw.get("file_properties.url")),
        "md5sum": _strip(raw.get("file_properties.md5sum")),
        "bp_covered": _to_int(raw.get("file_properties.bp_covered")),
        "num_intervals": _to_int(raw.get("file_properties.num_intervals")),
        "file_size": _to_int(raw.get("file_properties.file_size")),
        "file_format": _strip(raw.get("file_properties.file_format")),
        "file_schema": _strip(raw.get("file_properties.file_schema")),
        "release_date": _strip(raw.get("file_properties.release_date")),
    }

    if any(value is not None for value in biosample_characteristics.values()):
        payload["biosample_characteristics"] = biosample_characteristics

    if any(value is not None for value in subject_phenotypes.values()):
        payload["subject_phenotypes"] = subject_phenotypes

    if any(value is not None for value in experimental_design.values()):
        payload["experimental_design"] = experimental_design

    payload["provenance"] = provenance

    if any(value is not None for value in file_properties.values()):
        payload["file_properties"] = file_properties

    return payload


def build_payload_from_form(form: FormData) -> Track:
    raw: Dict[str, Any] = {k: form.get(k) for k in form.keys()}
    payload = _build_nested(raw)
    return Track(**payload)


def to_error_map(err: ValidationError) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    for item in err.errors(include_url=False):
        loc = item.get("loc", ())
        if isinstance(loc, tuple):
            key = ".".join([str(x) for x in loc if str(x) != "__root__"])
        else:
            key = str(loc)

        errors[key if key else "_form"] = item.get("msg", "Invalid value")

    return errors
