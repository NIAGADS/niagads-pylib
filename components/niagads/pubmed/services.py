import asyncio
import os
from niagads.utils.list import chunker
from typing import Dict, List, Optional, Union
from xml.etree import ElementTree

from aiohttp import ClientResponseError
from niagads.common.core import ComponentBaseMixin
from niagads.common.models.structures import Range
from niagads.requests.core import HttpClientSessionManager
from niagads.utils.sys import create_dir, verify_path
from pydantic import BaseModel, model_validator


class PubMedAuthor(BaseModel):
    last: Optional[str]
    first: Optional[str]
    initials: Optional[str]


class PubMedArticleMetadata(BaseModel):
    pmid: Optional[str]
    title: Optional[str]
    abstract: Optional[str]
    authors: List[PubMedAuthor] = []
    journal: Optional[str]
    year: Optional[str]
    mesh_terms: Optional[List[str]] = None


class PubMedQueryFilters(BaseModel):
    """
    Filters for querying PubMed articles.
    """

    keyword: Optional[List[str]] = None
    year: Optional[Union[int, Range]] = None
    mesh_term: Optional[List[str]] = None
    open_access_only: bool = False
    journal: Optional[List[str]] = None

    @model_validator(mode="after")
    def check_keyword_or_mesh(self) -> "PubMedQueryFilters":
        if not (self.keyword and any(self.keyword)) and not (
            self.mesh_term and any(self.mesh_term)
        ):
            raise ValueError(
                "At least one of 'keyword' or 'mesh_term' must be specified."
            )
        return self


class PubMedQueryService(ComponentBaseMixin):
    """
    Service for querying PubMed and extracting abstracts, titles, authors, and metadata.
    Supports filtering by publication year, MeSH term, and keyword searches in titles/abstracts.
    """

    EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov"
    ESEARCH_PATH = "/entrez/eutils/esearch.fcgi"
    EFETCH_PATH = "/entrez/eutils/efetch.fcgi"

    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        self._debug = debug
        self._verbose = verbose

        if self._debug:
            self.logger.setLevel = "DEBUG"
        else:
            self.logger.setLevel = "INFO"

        self.__email = email
        self.__api_key = api_key
        self.__rate_limit = 10 if self.__api_key else 3

    async def _rate_limited_request(
        self, path: str, params: dict, max_retries: int = 3
    ) -> str:
        """
        wrapper for E-utilities requests with rate limiting and retry logic.
        """

        delay = 1.0 / self.__rate_limit
        retries = 0
        while True:
            try:
                self.logger.debug(
                    f"Requesting: {self.EUTILS_BASE_URL}{path} with params: {params}"
                )
                async with HttpClientSessionManager(
                    base_url=self.EUTILS_BASE_URL
                ) as manager:
                    response_text = await manager.fetch_text(path, params)
                self.logger.debug(
                    f"Response received for {path}: {response_text[:500]}..."
                )
                await asyncio.sleep(delay)
                return response_text
            except ClientResponseError as err:
                self.logger.error(f"ClientResponseError for {path}: {err}")
                if err.status == 429:
                    self.logger.warning(
                        f"Rate limit exceeded, retrying after delay. Attempt {retries+1}"
                    )
                    # Use Retry-After header if available, else exponential backoff
                    retry_after = getattr(err, "headers", {}).get("Retry-After")
                    if retry_after:
                        await asyncio.sleep(float(retry_after))
                    else:
                        await asyncio.sleep(delay * (2**retries))
                    retries += 1
                    if retries > max_retries:
                        raise
                else:
                    raise

    async def __search(
        self,
        filters: PubMedQueryFilters,
        max_results: int = 20,
        count_only: bool = False,
    ) -> List[str] | int:
        """
        Search PubMed for articles matching the filter criteria.
        Returns a list of PubMed IDs (PMIDs) or, if count_only is True, just the count of matching PMIDs.
        Handles pagination internally if max_results > 10000 (NCBI E-utilities limit per request).
        """
        terms = []
        if filters.keyword:
            for kw in filters.keyword:
                terms.append(kw)

        # Handle year as int or Range
        if filters.year:
            if isinstance(filters.year, int):
                terms.append(f"{filters.year}[pdat]")
            elif isinstance(filters.year, Range):
                terms.append(f"{filters.year.start}:{filters.year.end}[pdat]")

        # Handle mesh_term as a list
        if filters.mesh_term:
            for mesh in filters.mesh_term:
                terms.append(f"{mesh}[MeSH Terms]")

        if filters.open_access_only:
            terms.append("free full text[filter]")

        if filters.journal:
            for journal in filters.journal:
                terms.append(f"{journal}[Journal]")
        query = " AND ".join(t for t in terms if t)

        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "xml",
        }

        if count_only:
            params["rettype"] = "count"
            params["retmax"] = 0
        else:
            retmax = 10000
            params["retmax"] = min(max_results, retmax)

        # Always add api_key and email if present
        if self.__api_key:
            params["api_key"] = self.__api_key
        if self.__email:
            params["email"] = self.__email

        response_text = await self._rate_limited_request(self.ESEARCH_PATH, params)

        if count_only:
            root = ElementTree.fromstring(response_text)
            count_elem = root.find(".//Count")
            return int(count_elem.text) if count_elem is not None else 0

        # Paginate through results if max_results > 10,000, fetching in batches and combining all PMIDs
        pmids = []
        retmax = 10000
        for retstart in range(0, max_results, retmax):
            batch_size = min(retmax, max_results - retstart)
            params["retmax"] = batch_size
            params["retstart"] = retstart
            # Always add api_key and email if present
            if self.__api_key:
                params["api_key"] = self.__api_key
            if self.__email:
                params["email"] = self.__email

            response_text = await self._rate_limited_request(self.ESEARCH_PATH, params)

            root = ElementTree.fromstring(response_text)
            batch_pmids = [id_elem.text for id_elem in root.findall(".//Id")]
            pmids.extend(batch_pmids)
            if len(batch_pmids) < batch_size:
                break
        return pmids

    async def fetch_article_metadata(
        self, pmids: List[str]
    ) -> List[PubMedArticleMetadata]:
        """
        Fetch metadata for a list of PMIDs from PubMed.
        Returns a list of PubMedArticleMetadata objects with title, abstract, authors, year, journal, etc.
        Handles batching internally if pmids > 200 (NCBI E-utilities limit per efetch request).
        """
        if not pmids:
            raise ValueError("No PMIDs provided to fetch_full_text.")

        all_articles = []
        batch_size = 200  # NCBI E-utilities efetch limit
        for start in range(0, len(pmids), batch_size):
            batch_pmids = pmids[start : start + batch_size]
            params = {"db": "pubmed", "id": ",".join(batch_pmids), "retmode": "xml"}
            # Always add api_key and email if present
            if self.__api_key:
                params["api_key"] = self.__api_key
            if self.__email:
                params["email"] = self.__email

            response_text = await self._rate_limited_request(self.EFETCH_PATH, params)

            root = ElementTree.fromstring(response_text)
            for article in root.findall(".//PubmedArticle"):
                medline = article.find("MedlineCitation")
                article_info = medline.find("Article") if medline is not None else None
                pmid = medline.findtext("PMID") if medline is not None else None
                title = (
                    article_info.findtext("ArticleTitle")
                    if article_info is not None
                    else None
                )
                abstract_elem = (
                    article_info.find("Abstract/AbstractText")
                    if article_info is not None
                    else None
                )
                abstract = abstract_elem.text if abstract_elem is not None else None
                authors = []
                if article_info is not None:
                    for author in article_info.findall("AuthorList/Author"):
                        last = author.findtext("LastName")
                        first = author.findtext("ForeName")
                        initials = author.findtext("Initials")
                        authors.append(
                            PubMedAuthor(last=last, first=first, initials=initials)
                        )
                journal_elem = (
                    article_info.find("Journal/Title")
                    if article_info is not None
                    else None
                )
                journal = journal_elem.text if journal_elem is not None else None
                year_elem = (
                    article_info.find("Journal/JournalIssue/PubDate/Year")
                    if article_info is not None
                    else None
                )
                year = year_elem.text if year_elem is not None else None
                mesh_terms = []
                if medline is not None:
                    for mesh_heading in medline.findall(
                        "MeshHeadingList/MeshHeading/DescriptorName"
                    ):
                        if mesh_heading.text:
                            mesh_terms.append(mesh_heading.text)
                all_articles.append(
                    PubMedArticleMetadata(
                        pmid=pmid,
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        journal=journal,
                        year=year,
                        mesh_terms=mesh_terms if mesh_terms else None,
                    )
                )
        return all_articles

    @staticmethod
    def filter_articles_by_keywords(
        articles: List[PubMedArticleMetadata], keywords: Optional[List[str]]
    ) -> List[PubMedArticleMetadata]:
        if not keywords:
            return articles
        keywords_lower = [k.lower() for k in keywords]

        def match(article: PubMedArticleMetadata):
            text = (article.title or "") + " " + (article.abstract or "")
            text = text.lower()
            return any(k in text for k in keywords_lower)

        return [a for a in articles if match(a)]

    async def find_articles(
        self,
        filters: PubMedQueryFilters,
        max_results: int = 20,
        ids_only: bool = False,
        counts_only: bool = False,
    ) -> List[PubMedArticleMetadata] | List[str] | int:
        """
        Search and fetch metadata for articles matching the filter criteria.
        If ids_only is True, return only a list of PMIDs.
        If counts_only is True, return only the count of matching articles (int).
        Otherwise, return a list of PubMedArticleMetadata objects.
        """
        result = await self.__search(
            filters=filters,
            max_results=max_results,
            count_only=counts_only,
        )
        if counts_only:
            return result
        if ids_only:
            return result
        articles = await self.fetch_article_metadata(result)
        return articles

    @staticmethod
    def extract_pmids(articles: List[PubMedArticleMetadata]) -> List[str]:
        """
        Extract a list of PubMed IDs (pmid) from a list of PubMedArticleMetadata objects.
        """
        return [a.pmid for a in articles if a.pmid]

    def __write_xml_to_path(
        self,
        pmid: str,
        xml: str,
        dir: str,
    ):
        """
        Write XML string to file in the specified directory, named as <pmid>.xml.
        """

        file_path = os.path.join(dir, f"{pmid}.xml")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(xml)
        except Exception as e:
            self.logger.exception(
                f"Failed to save XML for PMID {pmid} to {file_path}: {e}"
            )
            raise

    async def fetch_full_text(
        self, pmids: List[str], output_dir: str = None, batch_size: int = 200
    ) -> Union[Dict, int]:
        """
        Fetch full text for a list of PMIDs from PubMed Central (PMC) Open Access
        subset.

        Processes PMIDs in batches (default: 200 per batch) for efficient network
        usage. Each batch performs a single PMC lookup (elink.fcgi) for all PMIDs,
        mapping PubMed IDs to PMC IDs. For each mapped PMC ID, fetches the full text
        XML from PMC (efetch.fcgi).

        Args:
            pmids (List[str]): List of PubMed IDs to fetch full text for.
            output_dir (str, optional): Directory to write XML files. If None,
                returns results as a dict. Defaults to None.
            batch_size (int, optional): Number of PMIDs per batch. Defaults to 200.

        Returns:
            Dict[str, str] or int: If output_dir is None, returns a dict mapping
                'pmid' to XML string for each successfully retrieved full text. If
                output_dir is provided, writes each XML file to the specified
                directory (named <pmid>.xml) and returns the count of files written.

        Raises:
            ValueError: If no PMIDs are provided.

        Logs warnings for missing PMC mappings and failed fetches or writes.
        """

        if not pmids:
            raise ValueError("No PMIDs provided to fetch_full_text.")

        self.logger.info(
            f"Fetching full text for {len(pmids)} PMIDs (batch size = {batch_size})."
        )

        if output_dir is not None:
            if not verify_path(output_dir, isDir=True):
                self.logger.warning(
                    f"Output directory '{output_dir}' does not exist. Creating it."
                )
                create_dir(output_dir)

        full_text_query_params = {"db": "pmc", "rettype": "full", "retmode": "xml"}
        pmc_lookup_query_params = {"dbfrom": "pubmed", "db": "pmc", "retmode": "xml"}

        if self.__api_key:
            pmc_lookup_query_params["api_key"] = self.__api_key
            full_text_query_params["api_key"] = self.__api_key
        if self.__email:
            pmc_lookup_query_params["email"] = self.__email
            full_text_query_params["email"] = self.__email

        full_text_mappings = {}
        count = 0
        for batch_pmids in chunker(pmids, batch_size):
            pmc_lookup_query_params["id"] = ",".join(batch_pmids)

            xml_response = await self._rate_limited_request(
                "/entrez/eutils/elink.fcgi", pmc_lookup_query_params
            )
            root = ElementTree.fromstring(xml_response)
            # Map PMIDs to PMC IDs from batch response

            pubmed_ids = [
                id_elem.text for id_elem in root.findall(".//LinkSet/IdList/Id")
            ]
            pmc_ids = [
                f"PMC{id_elem.text}"
                for id_elem in root.findall('.//LinkSet/LinkSetDb[DbTo="pmc"]/Link/Id')
            ]

            pmc_to_pmid_mapping = dict(zip(pmc_ids, pubmed_ids))
            self.logger.debug(f"Mappings: {pmc_to_pmid_mapping}")

            # Warn for PMIDs with no PMC mapping
            missing_pmids = set(batch_pmids) - set(pubmed_ids)
            for missing_pmid in missing_pmids:
                self.logger.warning(f"No mapping for PMID {missing_pmid} to PMC found.")

            # Fetch full text for all mapped PMC IDs in a single batch
            if pmc_to_pmid_mapping:
                full_text_query_params["id"] = ",".join(pmc_to_pmid_mapping.keys())

                full_text_xml = await self._rate_limited_request(
                    self.EFETCH_PATH, full_text_query_params
                )

                root = ElementTree.fromstring(full_text_xml)
                for article in root.findall(".//article"):

                    pmc_id_elem = article.find(
                        "front/article-meta/article-id[@pub-id-type='pmcid']"
                    )

                    if pmc_id_elem is None or not pmc_id_elem.text:
                        raise ValueError("Missing PMC ID in article XML.")

                    pmc_id = pmc_id_elem.text
                    pubmed_id = pmc_to_pmid_mapping[pmc_id]
                    try:
                        xml_str = ElementTree.tostring(article, encoding="unicode")
                        if output_dir is None:
                            full_text_mappings[pubmed_id] = xml_str
                        else:
                            self.__write_xml_to_path(pubmed_id, xml_str, output_dir)
                        count += 1
                    except Exception as err:
                        self.logger.warning(
                            f"Failed to serialize XML for PMC ID {pmc_id} / PMID {pubmed_id}: {err}"
                        )

        if output_dir is None:
            self.logger.info(f"Retrieved {count} full text files from PMC.")
            return full_text_mappings

        else:
            self.logger.info(f"Wrote {count} full text XML files to {output_dir}.")
            return count
