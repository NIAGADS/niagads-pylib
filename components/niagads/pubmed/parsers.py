from typing import List, Dict, Optional
from xml.etree import ElementTree


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
