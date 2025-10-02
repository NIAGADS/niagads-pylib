from __future__ import annotations

import gzip
import io
import json
from collections import defaultdict
from typing import Dict, Any, Iterable, Optional, Set, List, Tuple


class GFF3Parser:
    def __init__(
        self,
        normalize_chroms: bool = True,
        add_chr_prefix: bool = True,
        keep_attributes: Optional[Set[str]] = None,
        transcript_like: Optional[Set[str]] = None,
        subfeature_like: Optional[Set[str]] = None,
    ):
        self.normalize_chroms = normalize_chroms
        self.add_chr_prefix = add_chr_prefix
        self.keep_attributes = keep_attributes
        self.transcript_like = transcript_like or {
            "transcript",
            "mRNA",
            "lnc_RNA",
            "miRNA",
            "snRNA",
            "snoRNA",
            "rRNA",
            "ncRNA",
            "pseudogenic_transcript",
        }
        self.subfeature_like = subfeature_like or {
            "exon",
            "CDS",
            "five_prime_UTR",
            "three_prime_UTR",
            "UTR",
            "intron",
            "start_codon",
            "stop_codon",
            "Selenocysteine",
        }

    def _open_any(self, path: str) -> io.TextIOBase:
        if path.endswith(".gz"):
            return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8")
        return open(path, "r", encoding="utf-8")

    def _norm_seqid(self, seqid: str) -> str:
        if not self.normalize_chroms:
            return seqid
        sid = seqid
        if self.add_chr_prefix and not sid.startswith("chr"):
            sid = f"chr{sid}"
        if sid == "chrMT":
            sid = "chrM"
        return sid

    def _parse_attrs(self, attr_field: str) -> Dict[str, Any]:
        if not attr_field or attr_field == ".":
            return {}
        out: Dict[str, Any] = {}
        for item in attr_field.split(";"):
            if not item:
                continue
            if "=" in item:
                k, v = item.split("=", 1)
                vals = [vv for vv in v.split(",") if vv != ""]
                out[k] = vals if len(vals) > 1 else (vals[0] if vals else "")
            else:
                out[item] = True
        if self.keep_attributes is not None:
            out = {k: v for k, v in out.items() if k in self.keep_attributes}
        return out

    def _strand_symbol(self, s: str) -> str:
        return "+" if s == "+" else "-" if s == "-" else "."

    def _sorted_children(self, children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            children,
            key=lambda n: (n["location"]["start"], n["location"]["end"], n["type"]),
        )

    def _strip_internals(self, n: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in n.items() if not k.startswith("_")}

    def _shape_gene_tree(self, root: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if root["type"] != "gene":
            return None

        ts, others = [], []
        for ch in root["children"]:
            (ts if ch["type"] in self.transcript_like else others).append(ch)

        new_ts = []
        for t in ts:
            sub, sub_others = [], []
            for ch in t["children"]:
                (sub if ch["type"] in self.subfeature_like else sub_others).append(ch)

            t_new = self._strip_internals(t)
            t_new["children"] = self._sorted_children(
                [self._strip_internals(x) for x in sub]
                + [self._strip_internals(x) for x in sub_others]
            )
            new_ts.append(t_new)

        g_new = self._strip_internals(root)
        g_children = self._sorted_children(
            new_ts + [self._strip_internals(x) for x in others]
        )
        g_new["children"] = g_children
        return g_new

    def gff3_to_gene_nested_json(self, gff_path: str) -> Dict[str, Any]:
        by_id: Dict[str, Dict[str, Any]] = {}
        roots_by_chrom: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        pending_children: Dict[str, List[str]] = defaultdict(list)
        anonymous_nodes_by_chrom: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        with self._open_any(gff_path) as fh:
            for line in fh:
                if not line or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 9:
                    continue
                seqid, source, ftype, start, end, score, strand, phase, attrs = parts
                chrom = self._norm_seqid(seqid)
                start_i = int(start)
                end_i = int(end)

                a = self._parse_attrs(attrs)
                fid = a.get("ID")
                if isinstance(fid, list):
                    fid = fid[0] if fid else None
                parent = a.get("Parent")
                if isinstance(parent, list):
                    parent = parent[0] if parent else None

                node = {
                    "id": fid,
                    "type": ftype,
                    "source": None if source == "." else source,
                    "location": {
                        "start": start_i,
                        "end": end_i,
                        "strand": self._strand_symbol(strand),
                    },
                    "attributes": a,
                    "children": [],
                    "_parent": parent,
                    "_seqid": chrom,
                }

                if fid:
                    by_id[fid] = node
                else:
                    anonymous_nodes_by_chrom[chrom].append(node)

                if parent and fid:
                    pending_children[parent].append(fid)

        for parent_id, child_ids in pending_children.items():
            parent_node = by_id.get(parent_id)
            if not parent_node:
                continue
            for cid in child_ids:
                ch = by_id.get(cid)
                if ch:
                    parent_node["children"].append(ch)

        for fid, node in by_id.items():
            parent_id = node.get("_parent")
            if parent_id and parent_id in by_id:
                continue
            roots_by_chrom[node["_seqid"]].append(node)

        for chrom, nodes in anonymous_nodes_by_chrom.items():
            roots_by_chrom[chrom].extend(nodes)

        records: Dict[str, List[Dict[str, Any]]] = {}
        for chrom, roots in roots_by_chrom.items():
            gene_trees = []
            for r in roots:
                shaped = self._shape_gene_tree(r)
                if shaped is not None:
                    gene_trees.append(shaped)
            if gene_trees:
                gene_trees.sort(
                    key=lambda g: (g["location"]["start"], g["location"]["end"])
                )
                records[chrom] = gene_trees

        return {"assembly": "GRCh38", "source": "Ensembl", "records": records}


# -------------------------- Example usage -----------------------------------
if __name__ == "__main__":
    parser = GFF3Parser(
        keep_attributes={
            "ID",
            "Parent",
            "gene_id",
            "gene_name",
            "transcript_id",
            "biotype",
        }
    )
    data = parser.gff3_to_gene_nested_json("Homo_sapiens.GRCh38.110.gff3.gz")
    print(json.dumps(data, indent=2))
