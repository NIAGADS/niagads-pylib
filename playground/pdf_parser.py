import json
from typing import List

import torch

# FIXME: EGA - after integration w/NIAGADS pylib
# from niagads.utils.sys import verify_path
from PyPDF2 import PdfReader
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
    logging as t_logging,
)


class PDFParser:
    """
    A class to parse scientific PDF files to text and perform conversion to structured JSON
    """

    def __init__(self, file: str, model: str, tokenLimit: int):
        self.__pdf = file  # FIXME: EGA - verify_path(file)
        self.__text = ""  # parsed text of the PDF
        self.__model = model  # LLM model to use for conversion
        self.__token_limit = tokenLimit
        self.__generator = None
        t_logging.set_verbosity_error()

    def set_token_limit(self, tokenLimit: int):
        self.__token_limit = tokenLimit

    def initialize_generator(self):
        """
        Loads a Hugging Face model and tokenizer for text generation.
        """
        # TODO: add quantization?
        tokenizer = AutoTokenizer.from_pretrained(self.__model)
        model = AutoModelForCausalLM.from_pretrained(
            self.__model, torch_dtype=torch.float16, device_map="auto"
        )
        self.__generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

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

    def get_generator(self):
        if self.__generator is None:
            self.initialize_generator()
        return self.__generator

    def chunk_text(self):
        """
        Splits the parsed text into chunks that fit within the model's token limit.
        """
        chunkSize = self.__token_limit
        # int(self.__token_limit / 2)  # need to leave tokens for response

        return [
            self.__text[i : i + chunkSize]
            for i in range(0, len(self.__text), chunkSize)
        ]

    def to_json(self, sections: List[str] = None):

        if self.__text is None:
            self.parse()

        if self.__generator is None:
            self.initialize_generator()

        if sections is None:
            sections = [
                "Abstract",
                "Introduction",
                "Methods",
                "Results",
                "Discussion",
                "Conclusion",
            ]

        # Define a prompt for the LLM to structure the text
        prompt = (
            f"You are a helpful assistant that extracts specific sections from a research paper.\n\n"
            f"Here is the paper text:\n{self.__text}\n\n"
            f"Extract and return the following sections, into structured JSON:\n"
            f"{', '.join(sections)}"
            f"\n\nPlease ensure that the JSON is well-formed and includes all relevant sections.\n\n"
        )

        # Generate structured JSON using the LLM
        response = self.__generator(
            prompt,
            max_new_tokens=100,
            do_sample=False,
            # , temperature=0.3
        )[0]["generated_text"]

        return response
        # TODO Parse the JSON string into a Python dictionary
