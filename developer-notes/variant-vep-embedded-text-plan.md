# Plan: Deterministic Embedded Text for Selected VEP Output

## Goal

Create compact, deterministic text for embeddings from selected VEP-derived annotations.

No LLM summary.
No variant ID.
No storage/indexing discussion.
No explanatory prose beyond searchable annotation terms.

---

## Core selection logic

Use the `most_severe_consequence.consequence_type` to decide what goes into the embedded text.

```text
If MSC is intergenic_consequences:
  embed MSC
  stop

If MSC is transcript_consequences:
  embed MSC
  add all unique regulatory_feature biotypes
  stop

If MSC is regulatory_feature_consequences:
  embed all unique regulatory_feature biotypes
  stop
```

Default:

```text
Ignore motif_feature_consequences.
Ignore intergenic_consequences unless MSC is intergenic.
Do not embed regulatory feature IDs.
Do not embed variant ID.
```

---

## What to include

### Transcript MSC

Include only present searchable fields:

```text
Transcript consequence <terms>.
Impact <impact>.
Coding consequence / Noncoding consequence.
Canonical transcript.   # if canonical true
MANE Select transcript. # if present
Gene <symbol>.
Gene biotype <biotype>.
Protein consequence <HGVSp>. # if present
TSS distance <value>.         # if present
Distance <value>.             # fallback if TSS distance absent
```

Then append regulatory biotypes if any exist:

```text
Regulatory feature biotypes enhancer, promoter.
```

Then append AF / predictor / overall classes.

Example:

```text
Transcript consequence upstream_gene_variant. Impact MODIFIER. Noncoding consequence. Canonical transcript. Gene DDX11L5. Gene biotype transcribed_unprocessed_pseudogene. TSS distance 1772. No protein consequence. Regulatory feature biotypes enhancer, promoter. Allele frequency common. CADD low. Enformer near_zero. Overall low_disruptive_evidence.
```

---

### Regulatory-feature MSC

Do **not** embed only the MSC regulatory feature. Embed all unique regulatory feature biotypes.

Example:

```text
Regulatory feature biotypes enhancer, promoter, open_chromatin_region. Allele frequency common. CADD low. Enformer elevated. Overall possible_regulatory_effect.
```

If there are no biotypes:

```text
Regulatory feature consequence regulatory_region_variant. Impact MODIFIER. Allele frequency common. CADD low. Enformer elevated. Overall possible_regulatory_effect.
```

---

### Intergenic MSC

Embed only the MSC and stop. Do not add regulatory or transcript context.

Example:

```text
Intergenic consequence intergenic_variant. Impact MODIFIER. Allele frequency common. CADD low. Enformer near_zero. Overall low_disruptive_evidence.
```

---

## What to exclude

Do not include:

```text
variant ID
chromosome / position / ref / alt
transcript IDs
regulatory feature IDs
motif feature IDs
null fields
raw predictor values unless explicitly needed
raw allele-frequency values unless explicitly needed
LLM-generated prose
```

---

## Derived classes

### Allele frequency

Flatten across all AF sources and populations.

```python
def max_af_nested(allele_frequency):
    if not allele_frequency:
        return None, None, None

    flattened = []

    for source, populations in allele_frequency.items():
        for population, value in (populations or {}).items():
            if value is not None:
                flattened.append((value, source, population))

    if not flattened:
        return None, None, None

    value, source, population = max(flattened, key=lambda x: x[0])
    return value, source, population


def af_class(max_af):
    if max_af is None:
        return "not_provided"
    if max_af < 0.001:
        return "rare"
    if max_af < 0.01:
        return "low_frequency"
    return "common"
```

Embedded text:

```text
Allele frequency rare.
Allele frequency low_frequency.
Allele frequency common.
```

---

### CADD

```python
def cadd_class(cadd_phred):
    if cadd_phred is None:
        return "not_available"
    if cadd_phred >= 30:
        return "very_high"
    if cadd_phred >= 20:
        return "high"
    if cadd_phred >= 10:
        return "moderate"
    return "low"
```

Embedded text:

```text
CADD low.
CADD moderate.
CADD high.
CADD very_high.
```

---

### Enformer

```python
def enformer_class(sad, sar):
    values = [abs(v) for v in (sad, sar) if v is not None]

    if not values:
        return "not_available"

    max_abs = max(values)

    if max_abs < 0.01:
        return "near_zero"
    if max_abs < 0.1:
        return "small"
    return "elevated"
```

Embedded text:

```text
Enformer near_zero.
Enformer small.
Enformer elevated.
```

---

## Implementation sketch

```python
from typing import Any


def unique_regulatory_biotypes(v: dict[str, Any]) -> list[str]:
    values = set()

    for c in v.get("regulatory_feature_consequences") or []:
        feature = c.get("feature") or {}
        biotype = feature.get("biotype")
        if biotype:
            values.add(biotype)

    return sorted(values)


def add_transcript_msc(parts: list[str], c: dict[str, Any]) -> None:
    feature = c.get("feature") or {}
    gene = feature.get("gene") or {}
    protein = feature.get("protein")

    terms = c.get("consequence_terms") or []
    if terms:
        parts.append(f"Transcript consequence {', '.join(terms)}.")

    if c.get("impact"):
        parts.append(f"Impact {c['impact']}.")

    if c.get("is_coding") is True:
        parts.append("Coding consequence.")
    elif c.get("is_coding") is False:
        parts.append("Noncoding consequence.")

    if feature.get("canonical") is True:
        parts.append("Canonical transcript.")

    if feature.get("mane_select"):
        parts.append("MANE Select transcript.")

    if gene.get("gene_symbol"):
        parts.append(f"Gene {gene['gene_symbol']}.")

    if gene.get("biotype"):
        parts.append(f"Gene biotype {gene['biotype']}.")

    if protein:
        if protein.get("hgvsp"):
            parts.append(f"Protein consequence {protein['hgvsp']}.")
        else:
            parts.append("Protein consequence.")
    else:
        parts.append("No protein consequence.")

    if feature.get("tssdistance") is not None:
        parts.append(f"TSS distance {feature['tssdistance']}.")
    elif feature.get("distance") is not None:
        parts.append(f"Distance {feature['distance']}.")


def add_intergenic_msc(parts: list[str], c: dict[str, Any]) -> None:
    terms = c.get("consequence_terms") or []
    if terms:
        parts.append(f"Intergenic consequence {', '.join(terms)}.")

    if c.get("impact"):
        parts.append(f"Impact {c['impact']}.")


def add_regulatory_biotypes(parts: list[str], biotypes: list[str]) -> None:
    if biotypes:
        parts.append("Regulatory feature biotypes " + ", ".join(biotypes) + ".")


def overall_class(impact, is_coding, af, cadd, enformer, protein_present, consequence_type):
    if consequence_type == "regulatory_feature_consequences":
        if enformer == "elevated":
            return "possible_regulatory_effect"
        return "limited_disruptive_evidence"

    if consequence_type == "intergenic_consequences":
        if af == "common" and cadd == "low" and enformer in {"near_zero", "small", "not_available"}:
            return "low_disruptive_evidence"
        return "limited_disruptive_evidence"

    if impact == "HIGH":
        if af == "common":
            return "high_impact_common"
        return "high_disruptive_evidence"

    if impact == "MODERATE":
        if is_coding is True or protein_present:
            if cadd in {"high", "very_high"}:
                return "protein_altering_predicted_deleterious"
            return "protein_altering"
        return "moderate_molecular_effect"

    if impact in {"LOW", "MODIFIER"}:
        if enformer == "elevated":
            return "possible_regulatory_effect"
        if af == "common" and cadd == "low" and enformer in {"near_zero", "small", "not_available"}:
            return "low_disruptive_evidence"
        return "limited_disruptive_evidence"

    return "insufficient_evidence"


def add_classes(parts: list[str], v: dict[str, Any], msc: dict[str, Any]) -> None:
    scores = v.get("predictor_scores", {})

    max_af, _, _ = max_af_nested(v.get("allele_frequency"))
    af = af_class(max_af)
    cadd = cadd_class(scores.get("cadd_phred"))
    enf = enformer_class(scores.get("enformer_sad"), scores.get("enformer_sar"))

    if af != "not_provided":
        parts.append(f"Allele frequency {af}.")

    if cadd != "not_available":
        parts.append(f"CADD {cadd}.")

    if enf != "not_available":
        parts.append(f"Enformer {enf}.")

    feature = msc.get("feature") or {}
    protein_present = bool(feature.get("protein"))

    overall = overall_class(
        impact=msc.get("impact"),
        is_coding=msc.get("is_coding"),
        af=af,
        cadd=cadd,
        enformer=enf,
        protein_present=protein_present,
        consequence_type=msc.get("consequence_type"),
    )

    parts.append(f"Overall {overall}.")


def build_embed_text(v: dict[str, Any]) -> str:
    msc = v["most_severe_consequence"]
    ctype = msc.get("consequence_type")
    parts = []

    if ctype == "intergenic_consequences":
        add_intergenic_msc(parts, msc)
        add_classes(parts, v, msc)
        return " ".join(parts)

    if ctype == "transcript_consequences":
        add_transcript_msc(parts, msc)
        add_regulatory_biotypes(parts, unique_regulatory_biotypes(v))
        add_classes(parts, v, msc)
        return " ".join(parts)

    if ctype == "regulatory_feature_consequences":
        biotypes = unique_regulatory_biotypes(v)
        if biotypes:
            add_regulatory_biotypes(parts, biotypes)
        else:
            terms = msc.get("consequence_terms") or []
            if terms:
                parts.append(f"Regulatory feature consequence {', '.join(terms)}.")
            if msc.get("impact"):
                parts.append(f"Impact {msc['impact']}.")

        add_classes(parts, v, msc)
        return " ".join(parts)

    return ""
```

---

## Final rule

```text
MSC intergenic → embed MSC only.
MSC transcript → embed MSC + all regulatory biotypes.
MSC regulatory → embed all regulatory biotypes.
Motif ignored.
```
