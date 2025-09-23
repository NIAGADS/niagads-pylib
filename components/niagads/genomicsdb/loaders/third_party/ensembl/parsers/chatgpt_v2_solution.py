from __future__ import annotations

import gzip
import io
from typing import Dict, Any, Optional


def open_text_file(path: str) -> io.TextIOBase:
    """Open a plain text or .gz GFF3 file as a text stream."""
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def strip_prefix(value: Optional[str]) -> Optional[str]:
    """Return the part after the first colon (e.g., 'gene:ENSG...' -> 'ENSG...')."""
    return None if value is None else value.split(":", 1)[-1]


def parse_id_and_parent(attribute_field: str) -> tuple[Optional[str], Optional[str]]:
    """Extract ID and Parent (first value if comma-separated); strip prefixes."""
    feature_id, parent_id = None, None
    if attribute_field and attribute_field != ".":
        for item in attribute_field.split(";"):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            first_value = value.split(",", 1)[0] if value else ""
            if key == "ID":
                feature_id = strip_prefix(first_value)
            elif key == "Parent":
                parent_id = strip_prefix(first_value)
    return feature_id, parent_id


def build_location(start_str: str, end_str: str, strand_str: str) -> Dict[str, Any]:
    """Build a simple location dict."""
    return {"start": int(start_str), "end": int(end_str), "strand": strand_str}


def ensure_array(document: Dict[str, Any], key: str) -> None:
    """Ensure document[key] exists and is a list."""
    if key not in document:
        document[key] = []


def ensure_other_features_map(document: Dict[str, Any]) -> None:
    """Ensure document['other_features'] exists and is a dict."""
    if "other_features" not in document:
        document["other_features"] = {}


def finalize_gene_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """Drop empty 'other_features' if unused and return the document."""
    if document.get("other_features") == {}:
        document.pop("other_features", None)
    return document


# Example usage:
# for gene_document in stream_gene_documents("Homo_sapiens.GRCh38.110.gff3.gz"):
#     print(gene_document)
#     break
