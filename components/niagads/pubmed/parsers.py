import difflib
from enum import auto
from typing import Dict, List, Optional
from xml.etree import ElementTree

import plotly.graph_objects as go
from niagads.common.core import ComponentBaseMixin
from niagads.enums.core import CaseInsensitiveEnum
from niagads.pubmed.services import PubMedArticleMetadata
from pydantic import BaseModel, Field


class ArticleSectionType(CaseInsensitiveEnum):
    """
    Enum for major article section types in full-text research papers.

    Members:
        INTRODUCTION: Introduction or background section.
        METHODS: Methods, materials, or experimental procedures section.
        DISCUSSION: Discussion, analysis, or interpretation section.
        CONCLUSION: Conclusion, summary, or findings section.
    """

    INTRODUCTION = auto()
    METHODS = auto()
    DISCUSSION = auto()
    CONCLUSION = auto()


class ArticleSection(BaseModel):
    """
    Ranked section title with match score for section identification.

    Attributes:
        section_type (ArticleSection): The type of section (e.g., INTRODUCTION, METHODS).
        section_index (int): Index of the section in the list of sections
        title (str): The actual section title string from the article.
        matched_title (str): the matched title string
        score (float): Goodness of match score (0.0 to 1.0).
    """

    section_type: ArticleSectionType
    section_index: int = Field(..., ge=0)
    title: str
    matched_title: str
    score: float = Field(..., ge=0.0, le=1.0)
    text: str

    def __str__(self):
        data = self.model_dump()
        data["text"] = f"{data['text'][:150]}..."


# Reference section titles for full-text article parsing
ARTICLE_SECTION_TITLES = {
    ArticleSectionType.INTRODUCTION: [
        "introduction",
        "background",
        "overview",
        "purpose",
        "aims",
    ],
    ArticleSectionType.METHODS: [
        "methods",
        "materials and methods",
        "experimental procedures",
        "methodology",
        "study design",
    ],
    ArticleSectionType.DISCUSSION: [
        "discussion",
        "interpretation",
        "commentary",
        "findings",
    ],
    ArticleSectionType.CONCLUSION: [
        "conclusion",
        "conclusions",
        "summary",
        "concluding remarks",
        "implications",
    ],
}


class PMCFullTextParser(ComponentBaseMixin):
    """
    Parser for extracting content from PMC full text XML.
    """

    def __init__(
        self,
        full_text_xml: str,
        pubmed_id: Optional[str] = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        self._debug = debug
        self._verbose = verbose
        if self._debug:
            self.logger.setLevel = "DEBUG"

        self.__raw_xml = full_text_xml
        self.__pubmed_id = pubmed_id

        self.__xml_root = None
        self.__sections = None
        self.__tables = None
        self.__figures = None

    def parse(self):
        """
        Parse the loaded XML and populate sections, tables, and figures member variables.
        """
        self.__xml_root = ElementTree.fromstring(self.__raw_xml)
        self._extract_tables()
        self._extract_sections()
        self._extract_figures()

    def _extract_tables(self) -> List[Dict]:
        """
        Extract tables from the loaded PMC full text XML.
        Returns a list of dicts with 'title', 'caption', and 'table_xml'.
        """
        # TODO: here or in application -> covert XML table to pandas table?
        self.__tables = []
        for table_wrap in self.__xml_root.findall(".//table-wrap"):
            title = table_wrap.findtext("label")
            caption_elem = table_wrap.find("caption")
            caption = None
            if caption_elem is not None:
                caption = "".join(caption_elem.itertext()).strip()
            table_elem = table_wrap.find("table")
            table_xml = (
                ElementTree.tostring(table_elem, encoding="unicode")
                if table_elem is not None
                else None
            )
            self.__tables.append(
                {"title": title, "caption": caption, "data": table_xml}
            )

    def _extract_section(self, sec_elem):
        title_elem = sec_elem.find("title")
        title = (
            title_elem.text.strip()
            if title_elem is not None and title_elem.text
            else None
        )
        text = " ".join(p.text.strip() for p in sec_elem.findall("p") if p.text)
        # Recursively append all subsection text
        for subsec in sec_elem.findall("sec"):
            sub_text = self._extract_section(subsec)["text"]
            if sub_text:
                text = f"{text} {sub_text}".strip()
        return {"title": title, "text": text}

    def _extract_sections(self) -> List[Dict]:
        """
        Recursively extract sections and subsections from the loaded PMC full text XML.
        Returns a list of dicts with 'title', 'text'. Subsection text is appended to the section.
        """

        self.__sections = []
        for sec in self.__xml_root.findall(".//body/sec"):
            self.__sections.append(self._extract_section(sec))

    def _extract_figures(self) -> List[Dict]:
        """
        Extract figures from the loaded PMC full text XML.
        Returns a list of dicts with 'label', 'caption', and 'graphic_href'.
        """
        self.__figures = []
        for fig_wrap in self.__xml_root.findall(".//fig"):
            label = fig_wrap.findtext("label")
            caption_elem = fig_wrap.find("caption")
            caption = None
            if caption_elem is not None:
                caption = "".join(caption_elem.itertext()).strip()
            graphic_elem = fig_wrap.find("graphic")
            graphic_href = (
                graphic_elem.get("{http://www.w3.org/1999/xlink}href")
                if graphic_elem is not None
                else None
            )
            self.__figures.append(
                {"label": label, "caption": caption, "graphic_href": graphic_href}
            )

    def get_tables(self) -> List[Dict]:
        if self.__raw_xml is None:
            self.parse()
        return self.__tables if self.__tables is not None else []

    def get_figures(self) -> List[Dict]:
        if self.__raw_xml is None:
            self.parse()
        return self.__figures if self.__figures is not None else []

    def fetch_matching_article_section(
        self,
        section: ArticleSectionType,
        title_generator: Optional[callable] = None,
        allow_fuzzy: bool = True,
    ) -> ArticleSection:
        """
        Find the best-matching section by title for a given type (e.g., intro, results, etc).

        Args:
            section (ArticleSectionType): The section type to match (e.g., INTRODUCTION).
            title_generator (Optional[callable]): Optional function to generate additional reference titles.
            allow_fuzzy (bool): If True, use fuzzy matching for section titles. Default=True

        Returns:
            ArticleSection: The best-matching section (with title, text, and score), or None if no match above threshold.

        Notes:
            - Returns immediately on exact or substring match (score 1.0 or 0.9).
            - Otherwise, returns the highest fuzzy match above threshold (default 0.8).
            - The returned ArticleSection includes the matched title, score, and full section text.
        """

        # validate the section
        article_section = ArticleSectionType(section)
        reference_titles = ARTICLE_SECTION_TITLES[article_section]
        if title_generator:
            reference_titles += [
                t.lower() for t in title_generator(str(article_section))
            ]

        best_match = None
        for index, section in enumerate(self.__sections):
            title = section.get("title")
            if title is None:
                continue
            title = title.lower()

            def make_ranked(score: float, match: str):
                return ArticleSection(
                    section_type=article_section,
                    section_index=index,
                    title=title,
                    matched_title=match,
                    score=score,
                    text=section["text"],
                )

            for ref_title in reference_titles:
                if title == ref_title:
                    return make_ranked(1.0, ref_title)
                if ref_title in title or title in ref_title:
                    # e.g., Results and Discussion
                    return make_ranked(0.9, ref_title)

                if allow_fuzzy:
                    score = difflib.SequenceMatcher(None, title, ref_title).ratio()
                    if best_match and score > best_match.score:
                        best_match = make_ranked(score, ref_title)

        if best_match and best_match.score >= 0.8:
            return best_match

        return None

    def get_sections(self) -> List[Dict]:
        """
        get all sections in dict form {title, text}
        """
        if self.__raw_xml is None:
            self.parse()
        if self.__sections is None:
            raise ValueError(
                f"Sections have not been parsed from the XML. Check input data."
            )

        return self.__sections


class PubMedArticleSummary(BaseModel):
    years: Dict[str, int] = Field(default_factory=dict)
    journals: Dict[str, int] = Field(default_factory=dict)
    mesh_terms: Dict[str, int] = Field(default_factory=dict)


class PubMedAnalyzer:
    """
    Analyzes a list of PubMedArticleMetadata for distributions of publication years, MeSH terms, and journals.
    """

    def __init__(self, articles: List[PubMedArticleMetadata]):
        self.__articles = articles
        self.__summary: PubMedArticleSummary = None

    def summarize(self) -> PubMedArticleSummary:
        years = {}
        journals = {}
        mesh_terms = {}
        for article in self.__articles:
            year = article.year
            if year:
                years[year] = years.get(year, 0) + 1
            journal = article.journal
            if journal:
                journals[journal] = journals.get(journal, 0) + 1
            mesh_list = getattr(article, "mesh_terms", None)
            if mesh_list:
                for mesh in mesh_list:
                    mesh_terms[mesh] = mesh_terms.get(mesh, 0) + 1
        self.__summary = PubMedArticleSummary(
            years=years,
            journals=journals,
            mesh_terms=mesh_terms,
        )

    @property
    def summary(self) -> Optional[PubMedArticleSummary]:
        """Return the cached PubMedSummary"""
        if not self.__summary:
            self.run()
        return self.__summary

    def plot_summary(self, top_n: Optional[int] = None):
        """
        Plot interactive bar charts for year, journal, and MeSH term distributions using Plotly.
        top_n: Number of top journals and MeSH terms to display. If None, show all.
        """
        if not self.__summary:
            self.summarize()

        # Year distribution (vertical bar chart)
        years = list(self.__summary.years.keys())
        year_counts = list(self.__summary.years.values())
        year_fig = go.Figure(
            data=[go.Bar(x=years, y=year_counts)],
        )
        year_fig.update_layout(
            title="Publication Year Distribution",
            xaxis_title="Year",
            yaxis_title="Count",
            xaxis_tickangle=-45,
            width=1000,
            height=400,
        )
        year_fig.show()

        # Journal distribution (horizontal bar chart)
        journal_dist = self.__summary.journals
        items = sorted(journal_dist.items(), key=lambda x: x[1], reverse=True)
        if top_n is not None:
            items = items[:top_n]
        journals, journal_counts = zip(*items) if items else ([], [])
        journal_fig = go.Figure(
            data=[go.Bar(y=list(journals), x=list(journal_counts), orientation="h")],
        )
        journal_fig.update_layout(
            title=f"{'Top ' + str(top_n) if top_n else 'All'} Journals",
            yaxis_title="Journal",
            xaxis_title="Count",
            width=1000,
            height=400,
        )
        journal_fig.update_yaxes(autorange="reversed")
        journal_fig.show()

        # MeSH term distribution (horizontal bar chart)
        mesh_dist = self.__summary.mesh_terms
        items = sorted(mesh_dist.items(), key=lambda x: x[1], reverse=True)
        if top_n is not None:
            items = items[:top_n]
        mesh_terms, mesh_counts = zip(*items) if items else ([], [])
        mesh_fig = go.Figure(
            data=[
                go.Bar(
                    y=list(mesh_terms),
                    x=list(mesh_counts),
                    orientation="h",
                    marker=dict(
                        line=dict(width=1, color="black"),
                        color="rgba(31, 119, 180, 0.7)",
                    ),
                    width=0.7,  # Thicker bars
                )
            ],
        )
        mesh_fig.update_layout(
            title=f"{'Top ' + str(top_n) if top_n else 'All'} MeSH Terms",
            yaxis_title="MeSH Term",
            xaxis_title="Count",
            width=1200,
            height=max(400, 30 * len(mesh_terms)),  # Dynamic height for all labels
            margin=dict(l=300, r=40, t=60, b=60),  # More left margin for long labels
            yaxis=dict(
                automargin=True,
                tickfont=dict(size=16),
            ),
            xaxis=dict(
                tickfont=dict(size=14),
            ),
        )
        mesh_fig.update_yaxes(autorange="reversed")
        mesh_fig.show()
