# Plan: Deterministic Embedded Text for VEP Annotation Search

## Goal

Create compact deterministic text for semantic search over VEP-derived variant annotations.

The embedded text should contain searchable annotation concepts from the selected VEP output and simple deterministic transforms.

No LLM generation is needed.

---

## Core idea

For each variant, build one annotation-dense text string from:

```text
selected biological consequence context
+ regulatory feature biotypes when relevant
+ source-qualified AF classes when allele frequency is present
+ deleteriousness phrases when CADD is present
+ regulatory-effect phrase when Enformer is present
+ proximity phrases from distance / tssdistance when present
+ gene-level LoF intolerance phrase when LoFtool is present on transcript consequences
```

Do not include fields or phrases for missing annotations.

---

## Selection logic

Use `most_severe_consequence.consequence_type`.

```text
If MSC is intergenic_consequences:
  embed MSC only
  stop

If MSC is transcript_consequences:
  embed MSC
  add gene-level LoFtool phrase, if present
  add all unique regulatory feature biotypes, if present
  stop

If MSC is regulatory_feature_consequences:
  embed all unique regulatory feature biotypes
  stop
```

Default:

```text
Ignore motif_feature_consequences unless they contain human-readable motif names or motif effects.
Ignore intergenic_consequences unless MSC is intergenic.
Do not embed regulatory feature IDs.
Do not add LoFtool outside transcript consequences.
```

---

## What belongs in embedded text

### Transcript MSC

Include when present:

```text
consequence terms
impact
coding / noncoding
gene symbol
gene ID
gene biotype
gene LoFtool-derived intolerance phrase
transcript ID
protein ID
protein change
proximity phrases from distance / tssdistance
```

Example:

```text
Transcript consequence upstream_gene_variant. Impact MODIFIER. Noncoding consequence. Transcript ENST00000421620. Gene DDX11L5. Gene ID ENSG00000236875. Gene biotype transcribed_unprocessed_pseudogene. Near transcription start site. Within 10kb of TSS. GnomAD allele frequency common. Weak predicted deleteriousness. Below top 10 percent of possible reference variants. Minimal predicted regulatory effect.
```

Coding example:

```text
Transcript consequence missense_variant. Impact MODERATE. Coding consequence. Gene TREM2. Gene ID ENSG00000186868. Gene biotype protein_coding. Gene shows high loss-of-function intolerance. Protein consequence p.Arg47His. GnomAD allele frequency rare. Strong predicted deleteriousness. Top 1 percent of possible reference variants.
```

---

### Regulatory feature consequences

Use unique regulatory feature biotypes.

```text
Regulatory feature biotypes enhancer, promoter, open_chromatin_region.
```

If MSC is regulatory feature:

```text
Regulatory feature biotypes enhancer, promoter. GnomAD allele frequency common. 1000Genomes allele frequency rare. Weak predicted deleteriousness. Below top 10 percent of possible reference variants. Strong predicted regulatory effect.
```

Do not add gene LoFtool phrases to regulatory-feature MSCs.

---

### Intergenic MSC

If MSC is intergenic, use only the intergenic annotation plus available derived phrases.

```text
Intergenic consequence intergenic_variant. Impact MODIFIER. GnomAD allele frequency common. Weak predicted deleteriousness. Below top 10 percent of possible reference variants. Minimal predicted regulatory effect.
```

Do not add transcript, regulatory, or LoFtool context.

---

## What to exclude

Exclude:

```text
variant ID
chromosome / position / ref / alt
raw numeric distance
raw AF values
raw predictor values
raw LoFtool values
null / missing field annotations
regulatory feature IDs
opaque motif feature IDs
long explanations
LLM prose
overall rollup classes
unqualified global AF statements
bare predictor labels
repeated predictor names in emitted phrases
LoFtool phrases outside transcript consequences
```

---

## Derived phrase helper rule

Helpers that may emit text return either:

```python
str | None
list[str] | None
```

Use `None` for missing values.

Do not return empty lists for missing values.

Use `list[str] | None` when one input should emit multiple separate embedding phrases.

---

## Distance / proximity handling

Do not embed raw numeric distance values.

Convert `tssdistance` and `distance` into proximity phrases.

### TSS distance

```python
def tss_distance_phrases(tssdistance: int | None) -> list[str] | None:
    if tssdistance is None:
        return None

    if tssdistance <= 1000:
        return ["near transcription start site", "within 1kb of TSS"]

    if tssdistance <= 10000:
        return ["near transcription start site", "within 10kb of TSS"]

    if tssdistance <= 100000:
        return ["proximal to transcription start site", "within 100kb of TSS"]

    return ["distal from transcription start site", "more than 100kb from TSS"]
```

### Gene distance

Use independently of `tssdistance`.

```python
def gene_distance_phrases(distance: int | None) -> list[str] | None:
    if distance is None:
        return None

    if distance <= 1000:
        return ["near gene", "within 1kb of gene"]

    if distance <= 10000:
        return ["near gene", "within 10kb of gene"]

    if distance <= 100000:
        return ["proximal to gene", "within 100kb of gene"]

    return ["distal from gene", "more than 100kb from gene"]
```

---

## Allele frequency handling

Allele frequency is source- and population-specific.

Do not collapse across all sources into one global phrase.

Use source-qualified class phrases.

```python
def af_class(value) -> str | None:
    if value is None:
        return None

    if value < 0.001:
        return "rare"

    if value < 0.01:
        return "low_frequency"

    return "common"


def af_phrases(allele_frequency) -> list[str] | None:
    if not allele_frequency:
        return None

    phrases = []

    for source, populations in allele_frequency.items():
        values = [v for v in (populations or {}).values() if v is not None]
        if not values:
            continue

        cls = af_class(max(values))
        if cls:
            phrases.append(f"{source} allele frequency {cls}")

    return phrases or None
```

Embed:

```text
GnomAD allele frequency common.
1000Genomes allele frequency rare.
```

Do not include raw AF values by default.

Do not emit anything if AF is absent.

---

## CADD handling

Do not embed bare score labels like:

```text
CADD low.
```

Use CADD internally to generate paired qualitative and percentile phrases.

The emitted phrases should not repeat the predictor name.

```python
def deleteriousness_phrases_from_cadd(cadd_phred) -> list[str] | None:
    if cadd_phred is None:
        return None

    if cadd_phred >= 30:
        return [
            "very strong predicted deleteriousness",
            "top 0.1 percent of possible reference variants",
        ]

    if cadd_phred >= 20:
        return [
            "strong predicted deleteriousness",
            "top 1 percent of possible reference variants",
        ]

    if cadd_phred >= 10:
        return [
            "moderate predicted deleteriousness",
            "top 10 percent of possible reference variants",
        ]

    return [
        "weak predicted deleteriousness",
        "below top 10 percent of possible reference variants",
    ]
```

Embed:

```text
Weak predicted deleteriousness.
Below top 10 percent of possible reference variants.
Moderate predicted deleteriousness.
Top 10 percent of possible reference variants.
Strong predicted deleteriousness.
Top 1 percent of possible reference variants.
Very strong predicted deleteriousness.
Top 0.1 percent of possible reference variants.
```

Do not emit anything if CADD is absent.

---

## Enformer handling

Use Enformer SAD/SAR only to produce a compact regulatory-effect phrase.

The emitted phrase should not repeat the model name.

```python
def regulatory_effect_phrase_from_enformer(sad, sar) -> str | None:
    values = [abs(v) for v in (sad, sar) if v is not None]

    if not values:
        return None

    max_abs = max(values)

    if max_abs < 0.01:
        return "minimal predicted regulatory effect"

    if max_abs < 0.1:
        return "small predicted regulatory effect"

    return "strong predicted regulatory effect"
```

Embed:

```text
Minimal predicted regulatory effect.
Small predicted regulatory effect.
Strong predicted regulatory effect.
```

Do not emit anything if Enformer values are absent.

---

## LoFtool handling

LoFtool is gene-level context and is only relevant for transcript consequences.

Do not embed the raw LoFtool score.

If present on the transcript consequence gene object, convert it to a gene loss-of-function intolerance phrase.

```python
def loftool_phrase(loftool) -> str | None:
    if loftool is None:
        return None

    if loftool < 0.1:
        return "gene shows high loss-of-function intolerance"

    if loftool < 0.5:
        return "gene shows moderate loss-of-function intolerance"

    return "gene shows low loss-of-function intolerance"
```

Embed:

```text
Gene shows high loss-of-function intolerance.
Gene shows moderate loss-of-function intolerance.
Gene shows low loss-of-function intolerance.
```

Do not emit anything if LoFtool is absent.

Do not add LoFtool phrases for regulatory-feature or intergenic MSCs.

---

## Consequence impact

Use VEP impact directly.

```text
Impact HIGH.
Impact MODERATE.
Impact LOW.
Impact MODIFIER.
```

---

## Coding / protein handling

### Coding status

Embed only if provided:

```text
Coding consequence.
Noncoding consequence.
```

### Protein consequence

If protein change exists:

```text
Protein consequence p.Arg47His.
```

If protein object exists but no HGVSp is available:

```text
Protein consequence.
```

Do not emit missing-protein phrases.

---

## Gene and biotype handling

Embed gene symbol, gene ID, and biotype when present.

```text
Gene TREM2.
Gene ID ENSG00000186868.
Gene biotype protein_coding.
Gene DDX11L5.
Gene ID ENSG00000236875.
Gene biotype transcribed_unprocessed_pseudogene.
```

Keep original biotype values.

---

## Regulatory biotype handling

Collect all unique regulatory feature biotypes.

```python
def unique_regulatory_biotypes(v):
    values = set()

    for c in v.get("regulatory_feature_consequences") or []:
        feature = c.get("feature") or {}
        biotype = feature.get("biotype")
        if biotype:
            values.add(biotype)

    return sorted(values)
```

Embed:

```text
Regulatory feature biotypes enhancer, promoter.
```

---

## Text helpers

```python
def append_phrase(parts, phrase):
    if phrase:
        parts.append(phrase.capitalize() + ".")


def append_phrases(parts, phrases):
    for phrase in phrases or []:
        append_phrase(parts, phrase)
```

---

## Text builders

### Transcript MSC

```python
def add_transcript_msc(parts, c, include_ids=True):
    feature = c.get("feature") or {}
    gene = feature.get("gene") or {}
    protein = feature.get("protein") or {}

    terms = c.get("consequence_terms") or []
    if terms:
        parts.append(f"Transcript consequence {', '.join(terms)}.")

    if c.get("impact"):
        parts.append(f"Impact {c['impact']}.")

    if c.get("is_coding") is True:
        parts.append("Coding consequence.")
    elif c.get("is_coding") is False:
        parts.append("Noncoding consequence.")

    if include_ids and feature.get("id"):
        parts.append(f"Transcript {feature['id']}.")

    if gene.get("gene_symbol"):
        parts.append(f"Gene {gene['gene_symbol']}.")

    if include_ids and gene.get("id"):
        parts.append(f"Gene ID {gene['id']}.")

    if gene.get("biotype"):
        parts.append(f"Gene biotype {gene['biotype']}.")

    append_phrase(parts, loftool_phrase(gene.get("loftool")))

    if protein:
        if protein.get("hgvsp"):
            parts.append(f"Protein consequence {protein['hgvsp']}.")
        else:
            parts.append("Protein consequence.")

        if include_ids and protein.get("id"):
            parts.append(f"Protein {protein['id']}.")

    append_phrases(parts, tss_distance_phrases(feature.get("tssdistance")))
    append_phrases(parts, gene_distance_phrases(feature.get("distance")))
```

---

### Regulatory biotypes

```python
def add_regulatory_biotypes(parts, biotypes):
    if biotypes:
        parts.append("Regulatory feature biotypes " + ", ".join(biotypes) + ".")
```

---

### Intergenic MSC

```python
def add_intergenic_msc(parts, c):
    terms = c.get("consequence_terms") or []

    if terms:
        parts.append(f"Intergenic consequence {', '.join(terms)}.")

    if c.get("impact"):
        parts.append(f"Impact {c['impact']}.")
```

---

## Final builder

```python
def build_embed_text(v, include_ids=True):
    msc = v["most_severe_consequence"]
    ctype = msc.get("consequence_type")
    scores = v.get("predictor_scores", {})
    parts = []

    if ctype == "intergenic_consequences":
        add_intergenic_msc(parts, msc)

    elif ctype == "transcript_consequences":
        add_transcript_msc(parts, msc, include_ids=include_ids)
        add_regulatory_biotypes(parts, unique_regulatory_biotypes(v))

    elif ctype == "regulatory_feature_consequences":
        add_regulatory_biotypes(parts, unique_regulatory_biotypes(v))

    else:
        terms = msc.get("consequence_terms") or []
        if terms:
            parts.append(f"Consequence {', '.join(terms)}.")
        if msc.get("impact"):
            parts.append(f"Impact {msc['impact']}.")

    append_phrases(parts, af_phrases(v.get("allele_frequency")))

    append_phrases(
        parts,
        deleteriousness_phrases_from_cadd(scores.get("cadd_phred")),
    )

    append_phrase(
        parts,
        regulatory_effect_phrase_from_enformer(
            scores.get("enformer_sad"),
            scores.get("enformer_sar"),
        ),
    )

    return " ".join(parts)
```

---

## Example embedded texts

### Transcript MSC with upstream consequence

```text
Transcript consequence upstream_gene_variant. Impact MODIFIER. Noncoding consequence. Transcript ENST00000421620. Gene DDX11L5. Gene ID ENSG00000236875. Gene biotype transcribed_unprocessed_pseudogene. Near transcription start site. Within 10kb of TSS. GnomAD allele frequency common. Weak predicted deleteriousness. Below top 10 percent of possible reference variants. Minimal predicted regulatory effect.
```

### Transcript MSC with regulatory biotypes

```text
Transcript consequence upstream_gene_variant. Impact MODIFIER. Noncoding consequence. Transcript ENST00000421620. Gene DDX11L5. Gene ID ENSG00000236875. Gene biotype transcribed_unprocessed_pseudogene. Near transcription start site. Within 10kb of TSS. Regulatory feature biotypes enhancer, promoter. GnomAD allele frequency common. 1000Genomes allele frequency rare. Weak predicted deleteriousness. Below top 10 percent of possible reference variants. Minimal predicted regulatory effect.
```

### Coding protein consequence

```text
Transcript consequence missense_variant. Impact MODERATE. Coding consequence. Gene TREM2. Gene ID ENSG00000186868. Gene biotype protein_coding. Gene shows high loss-of-function intolerance. Protein consequence p.Arg47His. GnomAD allele frequency rare. Strong predicted deleteriousness. Top 1 percent of possible reference variants.
```

### Regulatory MSC

```text
Regulatory feature biotypes enhancer, promoter. GnomAD allele frequency common. 1000Genomes allele frequency rare. Weak predicted deleteriousness. Below top 10 percent of possible reference variants. Strong predicted regulatory effect.
```

### Intergenic MSC

```text
Intergenic consequence intergenic_variant. Impact MODIFIER. GnomAD allele frequency common. Weak predicted deleteriousness. Below top 10 percent of possible reference variants. Minimal predicted regulatory effect.
```

---

## Final rule

Embed only text that improves semantic retrieval.

Good embedded text:

```text
biological consequence terms
gene symbols
gene IDs
gene / feature biotypes
transcript IDs
protein IDs
coding / noncoding
protein changes
proximity buckets
source-qualified AF classes
deleteriousness phrases paired with percentile context
regulatory effect phrases
gene-level LoF intolerance phrases for transcript consequences
```

Avoid:

```text
raw coordinates
raw distances
raw numeric scores
raw LoFtool scores
missing-field statements
opaque regulatory feature IDs
bare predictor labels such as CADD low
overall rollup classes
unqualified global AF statements
repeated predictor names in emitted phrases
LoFtool phrases outside transcript consequences
LLM-written explanations
```
