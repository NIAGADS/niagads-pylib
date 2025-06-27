import logging
from os.path import basename
from typing import List, Set, Union
from urllib.parse import unquote

from niagads.common.constants.ontologies import BiosampleType
from niagads.common.models.ontology import OntologyTerm
from niagads.database.models.metadata.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Provenance,
)
from niagads.database.models.metadata.track import Track
from niagads.utils.dict import print_dict
from niagads.utils.list import array_in_string, remove_duplicates, remove_from_list
from niagads.utils.logging import FunctionContextAdapter
from niagads.utils.string import (
    is_bool,
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

import requests


class MetadataTemplateParser:
    """Parser for FILER metadata templates.
    cleans and transforms to a JSON object that can be mapped to a track record"""

    def __init__(
        self,
        templateFile: str,
        filerDownloadUrl: str,
        datesAsStrings: bool = True,
        debug: bool = False,
        verbose: bool = False,
    ):
        self.logger: logging.Logger = FunctionContextAdapter(
            logging.getLogger(__name__), {}
        )

        self._debug = debug
        self._verbose = verbose

        self.__template = None
        self.__templateFile: str = templateFile
        self.__templateHeader = None
        self.__metadata: dict = None
        self.__filerDownloadUrl = filerDownloadUrl
        self.__datesAsStrings = datesAsStrings
        self.__load_template()

    def __load_template(self):
        if not self.__templateFile.startswith("http"):
            with open(self.__templateFile, "r") as fh:
                self.__template = fh.read().splitlines()

        else:
            response = requests.get(self.__templateFile)
            response.raise_for_status()
            self.__template = response.text.split("\n")

        self.__templateHeader = self.__template.pop(0).split("\t")
        if self.__template[-1] == "":  # sometimes extra line is present
            self.__template.pop()

        if self._debug:
            self.logger.debug(
                f"Done loading template (n = {len(self.__template)} entries)."
            )
            self.logger.debug(f"First row in template: {self.__template[0]}")

    def get_template_file_name(self):
        return self.__templateFile

    def get_metadata(self):
        return self.__metadata

    def log_section_header(self, label: str, **kwargs):
        # TODO: abstract  out into custom logger class
        self.logger.info("=" * 40, **kwargs)
        self.logger.info(label.center(40), **kwargs)
        self.logger.info("=" * 40, **kwargs)

    def parse(self, asTrackList: bool = False):
        """iterate over list of one or more raw metadata
        objects from FILER API and standardize; returns array of standardized metadata objects
        """
        self.log_section_header("Running Template Parser")

        entries = [
            dict(zip(self.__templateHeader, line.split("\t")))
            for line in self.__template
        ]
        self.__metadata = [
            (
                MetadataEntryParser(
                    e,
                    self.__filerDownloadUrl,
                    datesAsStrings=self.__datesAsStrings,
                    debug=self._debug,
                    verbose=self._verbose,
                ).to_track_record()
                if asTrackList
                else MetadataEntryParser(
                    e,
                    self.__filerDownloadUrl,
                    datesAsStrings=self.__datesAsStrings,
                    debug=self._debug,
                    verbose=self._verbose,
                ).to_json()
            )
            for e in entries
        ]
        return self.__metadata


class MetadataEntryParser:
    """parser for a FILER metadata entry from a template file:
    standardizes keys, extracts non-name info from name, cleans up

        keys:
            -- replace spaces with _
            -- lower case
            -- camelCase to snake_case
            -- rename fields, e.g., antibody -> antibody_target
            -- remove (s)
            -- identifier -> track_id

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
        datesAsStrings: bool = True,
        debug: bool = False,
        verbose: bool = False,
    ):
        self.logger = logging.getLogger(__name__)
        self._debug = debug
        self._verbose = verbose
        self.__entry = None
        self.__metadata = None
        self.__searchableTextValues = []
        self.__datesAsStrings = datesAsStrings
        self.__filerDownloadUrl = filerDownloadUrl

        self.set_entry(entry)

        if self._debug:
            self.logger.debug(f"Parsing: {print_dict(entry, pretty=False)}")

    def to_json(self):
        if self.__metadata is None:
            self.parse()
        return self.__metadata

    def to_track_record(self):

        if self.__metadata is None:
            self.parse()

        return Track(**self.__metadata)

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
            return to_date(value, returnStr=self.__datesAsStrings)

        return unquote(value)  # html entities

    def transform_key(self, key):
        # camel -> snake + lower case
        tValue: str = to_snake_case(key)
        tValue = tValue.replace(" ", "_")
        tValue = tValue.replace("(s)", "s")
        tValue = tValue.replace("#", "")
        return self.__rename_key(tValue)

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
        searchable_text

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

        # clean up and then add searchable text
        self.__metadata.update(
            {
                "searchable_text": ";".join(
                    remove_duplicates(self.__searchableTextValues, caseInsensitive=True)
                )
            }
        )

        # patches on assembled metadata
        self.__final_patches()

        if self._debug:
            self.logger.debug(f"Done parsing metadata entry: {self.__metadata}")

    def parse_basic_attributes(self):
        """Basic attributes, including setting track_id"""
        self.__metadata.update({"track_id": self.get_entry_attribute("identifier")})
        self.parse_descriptive_attributes()
        self.parse_genome_build()
        self.__metadata.update(
            {"is_download_only": self.get_entry_attribute("download_only", False)}
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

            self.__searchableTextValues.append(
                self.__clean_text(self.__metadata["name"])
            )

    def parse_genome_build(self):
        genomeBuild = self.get_entry_attribute("genome_build")
        if genomeBuild is not None:
            genomeBuild = "GRCh38" if "hg38" in genomeBuild else "GRCh37"
        self.__metadata.update({"genome_build": genomeBuild})

    def update_searchable_text(self, terms: List[str]):
        self.__searchableTextValues = self.__searchableTextValues + [
            self.__clean_text(v) for v in terms if v is not None
        ]

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

            if self._debug:
                self.logger.debug(f"term = {term}; term_id = {termId}; type = {bsType}")

            if bsType in ["Fractionation", "Timecourse"]:
                if self._verbose:
                    self.logger.warning(
                        f"Found '{bsType}' biosample type; assuming Fantom5 misclassified "
                        f"{term} for {self.get_entry_attribute('identifier')}: "
                        f"{self.get_entry_attribute('file_name')}; reassinging as `Cell Line`"
                    )
                bsType = "cell line"

            # TODO handle tissue categories, systems to be list
            characteristics = BiosampleCharacteristics(
                biosample=[OntologyTerm(term=term, term_id=termId)],
                tissue=[self.get_entry_attribute("tissue_category")],
                system=[self.get_entry_attribute("system_category")],
                life_stage=self.get_entry_attribute("life_stage"),
                biosample_type=None if bsType is None else str(BiosampleType(bsType)),
            )

            self.__metadata.update(
                {"biosample_characteristics": characteristics.model_dump()}
            )

            # pull out searchable text values
            searchableText: List[str] = (
                [
                    characteristics.life_stage,
                    str(characteristics.biosample_type),
                ]
                + characteristics.tissue
                + characteristics.system
                + [ot.term for ot in characteristics.biosample]
            )

            self.update_searchable_text(searchableText)

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

        self.__metadata.update({"experimental_design": design.model_dump()})
        self.update_searchable_text(
            [value for value in design.model_dump().values() if not is_bool(value)]
        )

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
                self.update_searchable_text(clist)

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

        self.__metadata.update({"provenance": provenance.model_dump()})
        self.update_searchable_text(
            [provenance.study, provenance.project, provenance.data_source]
        )

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

        self.__metadata.update({"file_properties": props.model_dump()})

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
                    return "gene"

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
        if "experimental_design" not in self.__metadata:
            self.parse_experimental_design()

        feature = self.__assign_feature_by_assay()
        if feature is None:
            feature = self.__assign_feature_by_analysis()
        if feature is None:
            feature = self.__assign_feature_by_classification()
        if feature is None:
            feature = self.__assign_feature_by_output_type()

        if feature is None:
            raise ValueError("No feature type mapped for track: ", self.__metadata)

        # variants have unnecessary prefixes
        # SAS GIH INDEL
        # SAS GIH SNV
        # SAS GIH SV
        # SAS SV
        if feature.endswith(" INDEL"):
            feature = "insertion/deletion variant (INDEL)"
        if feature.endswith(" SNV"):
            feature = "single nucleotide variant (SNV)"
        if feature.endswith(" SV"):
            feature = "structural variant (SV)"

        self.__metadata.update({"feature_type": feature})

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
        if source.startswith("ADSP"):
            source = source.replace("_", " ")
            version = None
        else:
            dsInfo = source.split("_", 1)
            source = dsInfo[0]
            version = dsInfo[1] if len(dsInfo) > 1 and dsInfo[0] else None

            if source == "FANTOM5" and "slide" in self.get_entry_attribute(
                "link_out_url"
            ):
                version = version + "_SlideBase"

            if array_in_string(source, ["INFERNO", "eQTL"]):
                # don't split on the _
                source = self.get_entry_attribute("data_source").replace("_", " ")
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
        return regex_replace(r"^[^GADB]*\/GADB", self.__filerDownloadUrl, url)

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
                    "searchable_text": self.__metadata["searchable_text"].replace(
                        f"{featureType} {featureType}", featureType
                    ),
                }
            )

    def __final_patches(self):
        # misc corrections to the data
        # update primary key label
        self.__clean_qtl_text()
