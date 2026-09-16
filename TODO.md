# TODOs

* fix bug w/ALFA loading from dbSNP VCF: wrap in {'ALFA':}.  TODO - patch db

* update schema dataset model to reflect new api model
* replace flat_dump w/context based serialization (will get passed to all children)
* can we move casesensitiveenum to common.types ? circular imports?!

## ETL

### FILER

* extract `is_cancer_cell`, `is_immune_cell` from track_description (probably) only relevant to ENCODE tracks
* there will be a new version of the template files with new column headers

```
NGENC7VGJXPUQ5  ENCODE  ENCFF078YRQ.bed.gz      3700    728458  IDR thresholded peaks   hg38    Ishikawa        Cell line       EFO:0005718     Female Reproductive     ENCSR000BKW     1       1_1     FOXA1   TF ChIP-seq   bed narrowPeak   62535   ${TARGETDIR}/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3    07/10/2025      12/12/2020      07/31/2025      https://tf.lisanwanglab.org/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/ENCFF078YRQ.bed.gz 2fd60d49de95ff2545c9292b3d46eb2a        wget https://tf.lisanwanglab.org/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/ENCFF078YRQ.bed.gz -P ${TARGETDIR}/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/   wget https://tf.lisanwanglab.org/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/ENCFF078YRQ.bed.gz.tbi -P ${TARGETDIR}/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/       https://www.encodeproject.org   https://www.encodeproject.org/files/ENCFF078YRQ/@@download/ENCFF078YRQ.bigBed   wget https://tf.lisanwanglab.org/GADB/Annotationtracks/Downloads/ENCODE/ENCFF078YRQ.bigBed -P ${TARGETDIR}/GADB/Annotationtracks/Downloads/ENCODE/     0fbb96a7db792b531812d6cf84a83f0c        TF ChIP-seq peaks       TF ChIP-seq IDR thresholded peaks       Biosample_summary=Homo sapiens Ishikawa treated with 0.02% dimethyl sulfoxide for 1 hour;Lab=Richard Myers, HAIB;ENCODE_internal_tags=RegulomeDB_1_0,RegulomeDB_2_0,RegulomeDB_2_1,ENCYCLOPEDIAv2,ENCYCLOPEDIAv1,RegulomeDB_2_2;Life_stage_age=adult 39 years;Reference=PMID:22710073;External_resources=GEO:GSM803444,UCSC-ENCODE-hg19:wgEncodeEH001586,FactorBook:ENCSR000BKW;Project=ENCODE;Award=U54HG004576;Experiment_date_released=2011-07-18;Submitted_track_name=rep1-pr1_vs_rep1-pr2.idr0.05.bfilt.regionPeak.bb;ENCODE_preferred_default=false;ENCODE_biosample_term_name=Ishikawa;ENCODE_cell_slims=cancer cell;ENCODE_system_slims=reproductive system;ENCODE_biosample_term_synonyms=Ishikawa cell;Analysis_title=ENCODE4 v1.6.1 GRCh38;GM=NR;Schema=bed6+4   Reproductive    Adult   ENCODE Ishikawa (repl. 1) TF ChIP-seq FOXA1 IDR thresholded peaks (narrowPeak) [Experiment: ENCSR000BKW] [Life stage: Adult]    forGenomeBrowser
```

### Bugs

* make wrappers for sqlalchemy.exc errors NoResultFound, MultipleResultFound so errors can be handled w/out importing from sqlalchemy?

## OWL ETL

* add flag to include objectproperties (e.g., for loading the relation ontology)
* resolve annotationproperties by skipping those not in the property iris
* move term_category to triple
* duplicates
* placeholders

## Top Priority

## Better VSCode

* Code Actions (e.g., for abstract classes)
* isort

## Documentation

* use lazydocs instead of sphinx
  
## Developer notes

* settings/configuration for `_api` bases; see <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage>
* microservices w/FastAPI - <https://dev.to/paurakhsharma/microservice-in-python-using-fastapi-24cc#using-nginx>
