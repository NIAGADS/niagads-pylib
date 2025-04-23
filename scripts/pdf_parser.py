import json

# FIXME: EGA - after integration w/NIAGADS pylib
# from niagads.utils.sys import verify_path
from PyPDF2 import PdfReader
from transformers import pipeline, GPT2Tokenizer, logging as t_logging


# GPT-2: 1024 tokens
# EleutherAI/gpt-neo-2.7B: 2048 tokens
# bigscience/bloom: 2048 tokens (for smaller models)


class PDFParser:
    """
    A class to parse scientific PDF files to text and perform conversion to structured JSON
    """

    def __init__(self, file: str, model: str = "gpt2", tokenLimit: int = 1024):
        self.__pdf = file  # FIXME: EGA - verify_path(file)
        self.__text = None  # parsed text of the PDF
        self.__model = model  # LLM model to use for conversion
        self.__token_limit = tokenLimit
        self.__llm_pipeline = pipeline("text-generation", model=self.__model)
        t_logging.set_verbosity_error()

    def set_token_limit(self, tokenLimit: int):
        self.__token_limit = tokenLimit

    def parse(self):
        """parses the PDF file and converts to text"""
        reader = PdfReader(self.__pdf)
        self.__text = ""

        for page in reader.pages:
            self.__text += page.extract_text()

    def get_text(self):
        """returns the parsed text of the PDF"""
        if self.__text is None:
            self.parse()
        return self.__text

    def get_num_input_tokens(self) -> int:
        """estimate number of tokens required to parse text"""
        tokenizer = GPT2Tokenizer.from_pretrained(self.__model)
        input_tokens = tokenizer.encode(self.__text, return_tensors="pt")
        return len(input_tokens[0])

    def chunk_text(self):
        """
        Splits the parsed text into chunks that fit within the model's token limit.
        """
        chunkSize = int(self.__token_limit / 2)  # need to leave tokens for response

        return [
            self.__text[i : i + chunkSize]
            for i in range(0, len(self.__text), chunkSize)
        ]

    def to_json(self):
        """
        Uses a Hugging Face LLM to generate structured data from the text.

        Args:
            text (str): Full text of the PDF.

        Returns:
            dict: Structured data containing title, abstract, and sections.
        """
        if self.__text is None:
            self.parse()

        structuredData = {"title": "", "abstract": "", "sections": []}
        chunks = self.chunk_text()
        for index, chunk in enumerate(chunks):
            print(f"chunk {index}")
            # for chunk in chunks:
            prompt = (
                f"Extract the title, abstract, and sections, and any tables from the following scientific paper text. "
                f"Return the result as a JSON object with keys: 'title', 'abstract', and 'sections'. "
                f"Each section should have a 'heading' and 'content'.\n\n"
                f"Text:\n{chunk}"
            )

            response = self.__llm_pipeline(
                prompt,
                max_new_tokens=self.__token_limit,
                num_return_sequences=1,
                temperature=0.7,
            )

        try:
            chunkResult = json.loads(response[0]["generated_text"])

            # Merge chunk results into the final structured data
            if "title" in chunkResult:
                structuredData["title"] = chunkResult["title"]
            if chunkResult["abstract"]:
                structuredData["abstract"] = chunkResult["abstract"]
            if "sections" in chunkResult:
                structuredData["sections"].extend(chunkResult["sections"])

        except (KeyError, json.JSONDecodeError):
            raise ValueError("Failed to parse LLM response into JSON.")

        return structuredData
