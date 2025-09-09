import logging
from typing import Dict, List, Optional, Union
from xml.etree import ElementTree

from niagads.common.models.structures import Range
from niagads.requests.core import HttpClientSessionManager
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


class PubMedQueryService:
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
        self.logger: logging.Logger = logging.getLogger(__name__)

        self.__email = email
        self.__api_key = api_key

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
            terms.append("pmc open access[filter]")
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

        async with HttpClientSessionManager(base_url=self.EUTILS_BASE_URL) as manager:
            response_text = await manager.fetch_text(self.ESEARCH_PATH, params)

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

            async with HttpClientSessionManager(
                base_url=self.EUTILS_BASE_URL
            ) as manager:
                response_text = await manager.fetch_text(self.ESEARCH_PATH, params)

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
            return []
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

            async with HttpClientSessionManager(
                base_url=self.EUTILS_BASE_URL
            ) as manager:
                response_text = await manager.fetch_text(self.EFETCH_PATH, params)

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
                all_articles.append(
                    PubMedArticleMetadata(
                        pmid=pmid,
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        journal=journal,
                        year=year,
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

    async def fetch_full_text(self, pmids: List[str]) -> Dict:
        """
        Fetch full text for a list of PMIDs.
        Returns dicts of 'pmid' : 'full_text' pairs.
        Attempts to fetch from PubMed Central (PMC) Open Access subset.
        """
        if not pmids:
            return []
        results = {}
        for pmid in pmids:
            full_text = None
            if pmid:
                # Try to get PMC ID via E-utilities elink
                params = {"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "xml"}
                try:
                    async with HttpClientSessionManager(
                        base_url=self.EUTILS_BASE_URL
                    ) as manager:
                        xml = await manager.fetch_text(
                            "/entrez/eutils/elink.fcgi", params
                        )
                    root = ElementTree.fromstring(xml)
                    pmc_id = None
                    for link in root.findall(".//LinkSetDb/Link/Id"):
                        pmc_id = link.text
                        break
                    if pmc_id:
                        # Try to fetch full text XML from PMC OAI
                        oai_params = {
                            "verb": "GetRecord",
                            "identifier": f"oai:pubmedcentral.nih.gov:{pmc_id}",
                            "metadataPrefix": "pmc",
                        }
                        try:
                            async with HttpClientSessionManager(
                                base_url=self.EUTILS_BASE_URL
                            ) as manager:
                                oai_xml = await manager.fetch_text(
                                    "/oai/oai.cgi", oai_params
                                )
                            # Just return the XML for now; parsing full text is complex
                            full_text = oai_xml
                        except Exception:
                            full_text = None
                except Exception:
                    full_text = None
            results.update({pmid: full_text})
        return results
