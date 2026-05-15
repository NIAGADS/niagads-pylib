from os.path import basename
from typing import Iterator, Union
from urllib.parse import unquote

import requests
from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.reference.ontologies.types import BiosampleType
from niagads.common.reference.xrefs.data_sources import ThirdPartyResources
from niagads.common.track.models import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Provenance,
)
from niagads.common.track.models.record import TrackRecord
from niagads.utils.string import (
    is_date,
    is_null,
    is_number,
    regex_extract,
    regex_replace,
    regex_split,
    to_date,
    to_numeric,
    to_snake_case,
)
from niagads.utils.sys import read_open_ctx

UCSC_TRACKS = ["Centromeres", "Repeats", "PhastCons", "Reference_Genome", "Telomeres"]
DATASOURCES_WITH_COLLECTIONS = [
    "RefSeq",
    "EpiMap",
    "ROADMAP",
    "Ensembl",
    "FANTOM5",
    "DASHR2",
    "Inferno",
]


class MetadataTemplateParser(ComponentBaseMixin):
    """Parser for FILER metadata templates.
    cleans and transforms to a JSON object that can be mapped to a track record"""

    def __init__(
        self,
        template_file: str,
        filer_download_url: str,
        debug: bool = False,
        verbose: bool = False,
        logger=None,
    ):
        super().__init__(debug=debug, verbose=verbose, logger=logger)

        self.__template_file: str = template_file
        self.__filer_download_url: str = filer_download_url
        self.__metadata_template: dict = None

    def parse(self):
        if self.__template_file.startswith("http"):
            response = requests.get(self.__template_file)
            response.raise_for_status()
            template = response.text.split("\n")
        else:  # local file
            with read_open_ctx(self.__template_file) as fh:
                template = fh.read().splitlines()

        header = template.pop(0).split("\t")
        if template[-1] == "":  # sometimes extra line is present
            template.pop()

        self.__metadata_template = [
            dict(zip(header, line.split("\t"))) for line in template
        ]

        if self._verbose:
            self.logger.info(
                f"Parsed {len(self.__metadata_template)} track entries from the metadata template."
            )

    def to_track_records(self) -> Iterator[TrackRecord]:
        for entry in self.__metadata_template:
            if self._verbose:
                self.logger.debug(f"{entry}")
            record = MetadataEntryParser(
                entry,
                self.__filer_download_url,
                debug=self._debug,
                verbose=self._verbose,
                logger=self.logger,
            ).to_track_record()

            if self._verbose:
                self.logger.debug(f"{record}")
            yield record


class MetadataEntryParser(ComponentBaseMixin):
    """parser for a FILER metadata entry from a template file

    keys:
        -- replace spaces with _
        -- lower case
        -- camelCase to snake_case
        -- rename fields, e.g., antibody -> antibody_target
        -- remove (s)
        -- identifier -> id

    values:
        -- genome build: hg38 -> GRCh38, hg19 -> GRCh37
        -- build biosample object
        -- build file info object
        -- build data source object
        -- extract [] fields from trackName
        -- original trackName --> description
        -- add feature type
        -- remove TF etc from assay

    """

    def __init__(
        self,
        entry: dict,
        filerDownloadUrl: str,
        debug: bool = False,
        verbose: bool = False,
        logger=None,
    ):
        super().__init__(debug=debug, verbose=verbose, logger=logger)
        self.__entry = None
        self.__metadata = None
        self.__filer_download_url = filerDownloadUrl

        self.set_entry(entry)

    def to_json(self):
        if self.__metadata is None:
            self.parse()
        return self.__metadata

    def to_track_record(self):

        if self.__metadata is None:
            self.parse()

        return TrackRecord(**self.__metadata)

    def parse_value(self, key: str, value):
        """catch numbers, booleans, nulls and html entities (b/c of text search)"""
        if is_null(value, naIsNull=True):
            return None

        if is_number(value):
            if "replicate" in key.lower():
                return value  # leave as string
            else:
                return to_numeric(value)

        if value in ["Not applicable", "Unknown"]:
            return None

        if "Not applicable;" in value:
            return value.replace("Not applicable;", "")

        if "date" in key.lower() and is_date(value):
            return to_date(value, return_str=True)

        return unquote(value)  # html entities

    def transform_key(self, key: str):
        # camel -> snake + lower case
        new_key: str = to_snake_case(key)
        new_key = new_key.replace(" ", "_")
        new_key = new_key.replace("(s)", "s")
        new_key = new_key.replace("#", "")
        return self.__rename_key(new_key)

    def set_entry(self, entry: dict):
        """clean keys and since iterating over
        the metadata anyway, catch nulls, numbers and convert from string
        """
        self.__entry = {
            self.transform_key(key): self.parse_value(key, value)
            for key, value in entry.items()
        }

    def get_entry_attribute(self, attribute: str, default: Union[str, int] = None):
        """get wrapper to handle KeyErrors"""
        return self.__entry[attribute] if attribute in self.__entry else default

    def parse(self):
        """parse the FILER metadata & transform/clean up
        returns parsed / transformed metadata

        if verifyTrack = True will query FILER to make sure that the track exists
        parser will return None if the track is not valid
        """

        """
        feature_type

        experimental_design
        provenance
        file_properties
        """

        self.__metadata = {}
        self.parse_basic_attributes()
        self.parse_biosample_characteristics()
        self.parse_experimental_design()
        self.parse_feature_type()  # depends on experimental design
        self.parse_cohorts()
        self.parse_provenance()
        self.parse_file_properties()

        # patches on assembled metadata
        self.__final_patches()

        if self._verbose:
            self.logger.debug(f"Done parsing metadata entry: {self.__metadata}")

    def parse_basic_attributes(self):
        """Basic attributes, including setting id"""
        self.__metadata.update({"id": self.get_entry_attribute("identifier")})
        self.parse_descriptive_attributes()
        self.parse_genome_build()
        self.__metadata.update(
            {
                "is_download_only": self.get_entry_attribute("track_type")
                == "downloadOnly"
            }
        )

    def parse_descriptive_attributes(self):
        """parse name and description"""
        name: str = self.get_entry_attribute("track_name")

        if name is None:  # take the file name and remove underscores, extension
            name = self.__parse_internal_url(
                self.get_entry_attribute("processed_file_download_url")
            )
            name = basename(name)
            name = name.replace(".bed.gz", "").replace("_", " ")
            self.__metadata.update({"name": name, "description": name})
        else:
            """
            remove paranthetical trailing notes on file types

            split points:
            bed*
            broadPeak
            idr_peak
            narrowPeak
            tss_peak

            pattern adapted from: https://stackoverflow.com/a/68862249 to only match closest parentheses
            """

            pattern = r"\s[(\[][^()\[\]]*?eak\)\s|\s\(bed[^()\[\]]*[)\]]\s"
            name = regex_split(pattern, name)

            self.__metadata.update(
                {
                    "name": name[0],
                    "description": self.get_entry_attribute("track_name"),
                }
            )

    def parse_genome_build(self):
        genomeBuild = self.get_entry_attribute("genome_build")
        if genomeBuild is not None:
            genomeBuild = "GRCh38" if "hg38" in genomeBuild else "GRCh37"
        self.__metadata.update({"genome_build": genomeBuild})

    # Possible Load-time TODOs
    # TODO map ontology terms to correct
    # TODO if cell line, map to cell type and add (or is this part of load?) or introduce cell line mapper?
    def parse_biosample_characteristics(self):
        term = self.get_entry_attribute("cell_type")

        if term is None:
            self.__metadata.update({"biosample_characteristics": None})

        else:
            termId = self.get_entry_attribute("biosamples_term_id")

            if term is not None and is_number(term):
                if self._verbose:
                    self.logger.warning(
                        f"Found numeric `cell_type` - {term} - for track {self.get_entry_attribute('identifier')}"
                    )
                    self.logger.warning(
                        f"Updating to {term} from `file_name` = {self.get_entry_attribute('file_name')}"
                    )
                term = (
                    unquote(self.get_entry_attribute("file_name"))
                    .split(".")[0]
                    .replace(":", " - ")
                )

            bsType = self.get_entry_attribute("biosample_type")

            # self.logger.debug(f"term = {term}; term_id = {termId}; type = {bsType}")

            if bsType in ["Fractionation", "Timecourse"]:
                if self._verbose:
                    self.logger.warning(
                        f"Found '{bsType}' biosample type; assuming Fantom5 misclassified "
                        f"{term} for {self.get_entry_attribute('identifier')}: "
                        f"{self.get_entry_attribute('file_name')}; reassinging as `Cell Line`"
                    )
                bsType = "cell line"

            tissue = self.get_entry_attribute("tissue_category")
            system = self.get_entry_attribute("system_category")
            lifestage = self.get_entry_attribute("life_stage")

            # TODO handle tissue categories, systems to be list
            characteristics = BiosampleCharacteristics(
                biosample=[
                    OntologyTerm(
                        term=term,
                        curie=f"#FILER-biosample:{term}" if termId is None else termId,
                    )
                ],
                tissue=(
                    None
                    if tissue is None
                    else [OntologyTerm(term=tissue, curie=f"#FILER-tissue:{tissue}")]
                ),
                system=None if system is None else [system],
                life_stage=(
                    None
                    if lifestage is None
                    else OntologyTerm(
                        term=lifestage, curie=f"FILER-lifestage:{lifestage}"
                    )
                ),
                biosample_type=None if bsType is None else [BiosampleType(bsType)],
            )

            self.__metadata.update(
                {
                    "biosample_characteristics": characteristics
                }  # .model_dump(exclude=None)}
            )

    def parse_experimental_design(self):
        assay = self.__parse_assay()  # parse out `assays` and `analyses`

        design = ExperimentalDesign(
            is_lifted=self.__parse_is_lifted(),
            assay=assay["assay"],
            data_category=self.__parse_data_category(),
            analysis=assay["analysis"],
            classification=self.get_entry_attribute("classification"),
            output_type=self.__parse_output_type(),
            antibody_target=self.get_entry_attribute("antibody_target"),
        )

        self.__metadata.update({"experimental_design": design.model_dump(exclude=None)})

    # FIXME: see NGEQC01308 -> getting a cell type instead
    def parse_cohorts(self):
        info = self.__clean_list(
            self.get_entry_attribute("track_description"), delim=";"
        )
        if info is not None:
            cohorts: str = regex_extract("sample_group=([^;]*)", info)
            if cohorts is not None:
                clist = cohorts.split(",")
                self.__metadata.update({"cohorts": clist})

    def parse_provenance(self):
        dataSource, version = self.__parse_data_source()

        provenance = Provenance(
            data_source=dataSource,
            release_version=version,
            download_date=self.get_entry_attribute("download_date"),
            download_url=self.__parse_generic_url(
                self.get_entry_attribute("raw_file_url")
            ),
        )

        info = self.__clean_list(
            self.get_entry_attribute("track_description"), delim=";"
        )

        if info is not None:
            provenance.project = regex_extract("Project=([^;]*)", info)

            provenance.study = regex_extract("study_name=([^;]*)", info)
            if provenance.study is None:
                provenance.study = regex_extract("study_label=([^;]*)", info)

            provenance.accession = regex_extract("dataset_id=([^;]*)", info)
            if provenance.accession is None:
                provenance.accession = regex_extract("study_id=([^;]*)", info)

            publications: str = regex_extract("study_pubmed_id=([^;]*)", info)

            # FIXME: failed a regexp test; need to catch 'Not yet published PMID'
            # also need to trim b/c getting PMID: ID instead of PMID:ID

            # first create a set to make sure pubmed_ids are unique, then convert
            # to list because sets are not JSON serializable
            provenance.pubmed_id = (
                None
                if publications is None
                else list(
                    set(
                        [
                            f"PMID:{id}" if "PMID:" not in id else id
                            for id in publications.split(",")
                        ]
                    )
                )
            )

        # FIXME temporary patches
        if dataSource == "MiGA":
            provenance.data_source = "NIAGADS DSS"
            provenance.accession = "NG00105"
            provenance.study = "MiGA - Microglia Genomic Atlas"
        if dataSource.startswith("NG00102"):
            provenance.accession = provenance.data_source
            provenance.data_source = "NIAGADS DSS"
            provenance.study = provenance.release_version
            provenance.release_version = None

        if dataSource in DATASOURCES_WITH_COLLECTIONS:
            provenance.accession = self.get_entry_attribute("data_source")

        self.__metadata.update({"provenance": provenance.model_dump(exclude=None)})

    def parse_file_properties(self):
        format, schema = self.__parse_file_format()

        props = FileProperties(
            file_name=self.get_entry_attribute("file_name"),
            url=self.__parse_internal_url(
                self.get_entry_attribute("processed_file_download_url")
            ),
            md5sum=self.get_entry_attribute("md5sum"),
            bp_covered=self.get_entry_attribute("bp_covered"),
            num_intervals=self.get_entry_attribute("num_intervals"),
            file_size=self.get_entry_attribute("file_size"),
            file_format=format,
            file_schema=schema,
            release_date=self.get_entry_attribute("filer_release_date"),
        )

        self.__metadata.update({"file_properties": props.model_dump(exclude=None)})

    def __assign_feature_by_assay(self):
        assay = self.__metadata["experimental_design"].get("assay")
        if assay is not None:
            if "QTL" in assay:
                return assay
            if "TF" in assay:
                return "transcription factor binding site"
            if "Histone" in assay:
                return "histone modification"
            if assay in ["Small RNA-seq", "short total RNA-seq"]:
                return "small non-coding RNA"
            if assay in ["FAIRE-seq", "DNase-seq", "ATAC-seq"]:
                return "chromatin accessibility"
            if assay == "PRO-seq":
                return "enhancer"
            if assay in ["eCLIP", "iCLIP", "RIP-seq"]:
                return "protein-RNA crosslink or binding sites"

        return None

    def __assign_feature_by_analysis(self):

        analysis: str = self.__metadata["experimental_design"].get("analysis")
        outputType: str = self.__metadata["experimental_design"].get("output_type")
        if analysis is not None:
            if analysis == "annotation":
                # check output type
                if "gene" in outputType.lower():
                    return "GENE"

                if "variant" in outputType.lower():
                    return "variant"

                # check track_description
                # e.g., All lncRNA annotations
                trackDescription = self.get_entry_attribute("track_description")
                if trackDescription is not None and "annotation" in trackDescription:
                    return regex_extract(
                        r"All (.+) annotation",
                        self.get_entry_attribute("track_description"),
                    )
            if "QTL" in analysis:
                return analysis

        return None

    def __assign_feature_by_output_type(self):
        outputType: str = self.__metadata["experimental_design"].get("output_type")
        if outputType is not None:
            if "enhancer" in outputType.lower():
                return "enhancer"
            if "methylation state" in outputType:
                state, loc = outputType.split(" at ")
                return loc + " " + state
            if "microrna target" in outputType.lower():
                return "microRNA target"
            if "microRNA" in outputType:
                return "microRNA"
            if "exon" in outputType:
                return "exon"
            if "transcription start sites" in outputType or "TSS" in outputType:
                return "transcription start site"
            if "transcribed fragments" in outputType:
                return "transcribed fragment"

            if outputType in ["footprints", "hotspots"]:
                # TODO: this may need to be updated, as it varies based on the assay type
                return outputType

            # should have been already handled, but just in case
            if outputType in ["clusters", "ChromHMM", "Genomic Partition"]:
                return None

            if outputType.startswith("Chromatin"):  # standardize case
                return outputType.lower()

            # peaks are too generic
            # TODO: handle peaks & correctly map, for now
            # just return
            # but there are some "enhancer peaks", which is why
            # this test is 2nd
            if "peaks" in outputType:
                return outputType

        return outputType

    def __assign_feature_by_classification(self):
        classification: str = self.__metadata["experimental_design"].get(
            "classification"
        )
        if classification is not None:
            classification = classification.lower()
            if "histone-mark" in classification:
                return "histone modification"
            if "chip-seq" in classification or "chia-pet" in classification:
                if "ctcf" in classification:
                    return "CTCF-biding site"
                if "ctcfl" in classification:
                    return "CTCFL-binding site"
                if classification.startswith("tf "):
                    return "transcription factor binding site"
                if "chromhmm" in classification:
                    return "enhancer"
            if classification == "rna-pet clusters":
                return "RNA-PET cluster"

        return None

    def parse_feature_type(self):
        # FIXME: this is now genomics db only, much improved data category captures this
        self.__metadata.update({"feature_type": "REGION"})

    def __parse_data_category(self):
        category = self.get_entry_attribute("data_category")
        if category is not None:
            category = category.lower()
            if category == "called peaks expression":
                category = "called peaks"
            if category == "qtl":
                category = "QTL"

        return category

    def __parse_assay(self) -> dict:
        analysis = None

        classification = self.get_entry_attribute("classification")
        if classification == "ChIP-seq consolidated ChromHMM":
            analysis = "ChromHMM"

        assay = self.get_entry_attribute("assay")

        if assay is not None:
            assay = assay.replace("-Seq", "-seq")  # consistency

            if "ChromHMM" in assay:
                analysis = assay
                assay = "ChIP-seq"

            elif assay.lower() == "annotation":
                assay = None
                analysis = "annotation"

            elif assay in ["eQTL", "sQTL"]:
                analysis = assay
                assay = None

            # TODO: need to check output type b/c assay type may need to be updated
            # e.g. DNASeq Footprinting if output_type == footprints
            elif "DNase" in assay:
                assay = "DNase-seq"

        return {"assay": assay, "analysis": analysis}

    def __parse_data_source(self):
        # FIXME: most of the SKIP_DATASOURCE list in the loader gets parsed incorrectly here
        source = self.get_entry_attribute("data_source")
        version = None

        if source.islower():
            source = source.title()

        if source in UCSC_TRACKS:
            source = "UCSC"

        try:
            # we are good
            ThirdPartyResources(source)
            source = source.replace("_", " ")
        except:
            # there is versioning info in the source
            dsInfo = source.split("_", 1)
            source = dsInfo[0]
            version = dsInfo[1] if len(dsInfo) > 1 else None

            if source.startswith(tuple(DATASOURCES_WITH_COLLECTIONS)):
                if source == "FANTOM5" and "slide" in self.get_entry_attribute(
                    "link_out_url"
                ):
                    version = "SlideBase"
                else:
                    version = None

        return source, version

    def __parse_file_format(self):
        formatInfo = self.get_entry_attribute("file_format").split(" ")
        format = formatInfo[0]
        schema = None

        if len(formatInfo) == 1:
            if "bed" in format:
                schema = format
                format = "bed"
        else:
            schema = (
                formatInfo[1]
                if len(formatInfo) == 2
                else formatInfo[1] + "|" + formatInfo[2]
            )

        return format, schema

    def __parse_generic_url(self, url):
        """handle common fixes to all URL fields"""

        if url is not None and "wget" in url:
            url = url.split(" ")[1]

        return url

    def __parse_internal_url(self, url):
        """correct domain and other formatting issues"""
        url = self.__parse_generic_url(url)
        return regex_replace(r"^[^GADB]*\/GADB", self.__filer_download_url, url)

    def __parse_is_lifted(self):
        genomeBuild = self.get_entry_attribute("genome_build")
        dataSource = self.get_entry_attribute("data_source")

        lifted = False
        if genomeBuild is not None:
            lifted = "lifted" in genomeBuild

        if not lifted and dataSource is not None:
            lifted = "lifted" in dataSource

        return lifted

    def __parse_output_type(self):
        outputType = self.get_entry_attribute("output_type")
        if outputType.lower() in [
            "chromatin interactions",
            "genomic partition",
            "enhancer peaks",
        ]:
            outputType = outputType.lower()

        return outputType

    def __clean_text(self, s: str):
        """
        clean text to remove symbols (;:,) and extra spaces
        Args:
            value (str): string to clean
        Returns:
            cleaned string
        """
        cleanStr = regex_replace(";|,|:", "", s)
        return " ".join(cleanStr.split())  # hack to remove multiple consecutive spaces

    def __clean_list(self, s: str, delim: str = ";"):
        """
        wrapper to clean ';' delimited list of values; removes extra spaces
        can change delimiter w/ delim option

        Args:
            s (str): string to clean
            delim (str, optional): new delimiter. Defaults to ';'.
        """
        if s is None:
            return s

        cleanStr = s.replace("; ", ";")
        return delim.join(
            cleanStr.split(";")
        )  # hack to remove multiple consecutive spaces

    def __rename_key(self, key):
        match key:
            case "antibody":
                return "antibody_target"
            case "downloaded_date":
                return "download_date"
            case "processed_file_md5":
                return "md5sum"
            case "raw_file_md5":
                return "raw_file_md5sum"
            case "technical_replicate":  # for consistency
                return "technical_replicates"
            case "date_added_to_filer":
                return "filer_release_date"
            case _:
                return key

    def __clean_qtl_text(self):
        """xQTL track names/descriptions have consecutive duplicate text:
        e.g. NG00102_Cruchaga_pQTLs Cerebrospinal fluid pQTL pQTL INDEL nominally significant associations
        remove the duplicate feature type from the text field
        """

        featureType = self.__metadata["feature_type"]

        if "QTL" in featureType:
            self.__metadata.update(
                {
                    "name": self.__metadata["name"].replace(
                        f"{featureType} {featureType}", featureType
                    ),
                    "description": self.__metadata["description"].replace(
                        f"{featureType} {featureType}", featureType
                    ),
                }
            )

    def __final_patches(self):
        # misc corrections to the data
        # update primary key label
        self.__clean_qtl_text()
