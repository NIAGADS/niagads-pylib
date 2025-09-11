from typing import Dict, List, Optional
from xml.etree import ElementTree

import plotly.graph_objects as go
from niagads.pubmed.services import PubMedArticleMetadata
from pydantic import BaseModel, Field


class PMCFullTextParser:
    """
    Parser for extracting content from PMC full text XML.
    """

    def __init__(self, full_text_xml: str, pubmed_id: Optional[str] = None):
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

    def _extract_sections(self) -> List[Dict]:
        """
        Recursively extract sections and subsections from the loaded PMC full text XML.
        Returns a list of dicts with 'title', 'text'. Subsection text is appended to the section.
        """

        def extract_sec(sec_elem):
            title_elem = sec_elem.find("title")
            title = (
                title_elem.text.strip()
                if title_elem is not None and title_elem.text
                else None
            )
            text = " ".join(p.text.strip() for p in sec_elem.findall("p") if p.text)
            # Recursively append all subsection text
            for subsec in sec_elem.findall("sec"):
                sub_text = extract_sec(subsec)["text"]
                if sub_text:
                    text = f"{text} {sub_text}".strip()
            return {"title": title, "text": text}

        self.__sections = []
        for sec in self.__xml_root.findall(".//body/sec"):
            self.__sections.append(extract_sec(sec))

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

    def get_sections(
        self,
        titles: Optional[List[str]] = None,
        title_matcher: Optional[callable] = None,
    ) -> List[Dict]:
        """
        Return sections, optionally filtering by a list of section titles (case-insensitive).
        If titles is None, return all sections.
        Optionally, a title_matcher callable can be provided for semantic/fuzzy/LLM-based matching.
        """
        if self.__raw_xml is None:
            self.parse()
        if self.__sections is None:
            return []
        if not titles:
            return self.__sections
        if title_matcher is not None:
            raise NotImplementedError(
                "LLM/semantic title matching is not yet implemented. Please provide a callable in the future."
            )
        titles_lower = set(t.lower() for t in titles)
        return [
            s
            for s in self.__sections
            if s["title"] and s["title"].lower() in titles_lower
        ]


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
