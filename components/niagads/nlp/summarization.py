"""
Utilities for prompt-driven text summarization using Hugging Face generation models.

Implementation informed by Hugging Face pipeline and text generation docs:
https://huggingface.co/docs/transformers/en/main_classes/pipelines
"""

import json
import logging
import re
from functools import lru_cache
from typing import Optional, Union

from niagads.common.core import ComponentBaseMixin
from niagads.nlp.llm_types import LLM, NLPModelType
from niagads.nlp.models import SummaryPrompt
from transformers import pipeline


class TextSummaryGenerator(ComponentBaseMixin):
    """Generate structured summaries from normalized prompt packets."""

    def __init__(
        self,
        model: LLM = LLM.QWEN2_5_7B_INSTRUCT,
        debug: bool = False,
        verbose: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(debug=debug, verbose=verbose, logger=logger)
        self.__model = LLM(model)
        self.__pipeline = self.__initialize_pipeline(self.__model)
        self.logger.debug(f"Initialized text summary generator: {self.__model}")

    def __repr__(self) -> str:
        return f"TextSummaryGenerator(model={self.__model!r})"

    @staticmethod
    @lru_cache(maxsize=3)
    def __initialize_pipeline(model: LLM):
        """
        Get or load a cached text-generation pipeline for summarization.

        Args:
            model (LLM): The summarization model to load.

        Returns:
            Pipeline: Cached Hugging Face text-generation pipeline.
        """
        LLM.validate(model, NLPModelType.SUMMARIZATION)
        return pipeline(
            task="text-generation",
            model=str(model),
            tokenizer=str(model),
        )

    def __build_prompt(self, prompt: SummaryPrompt) -> str:
        tokenizer = self.__pipeline.tokenizer
        if not (hasattr(tokenizer, "chat_template") and tokenizer.chat_template):
            raise ValueError(
                f"Tokenizer for {self.__model} does not expose a chat template."
            )

        return tokenizer.apply_chat_template(
            [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt},
            ],
            tokenize=False,
            add_generation_prompt=True,
        )

    def render_prompt(self, prompt: SummaryPrompt) -> str:
        """
        Render a prompt using the tokenizer chat template.

        Args:
            prompt (SummaryPrompt): Prompt payload for summary generation.

        Returns:
            str: Rendered model-ready prompt text.
        """
        return self.__build_prompt(prompt)

    @staticmethod
    def extract_json(text: str) -> dict:
        """Extract JSON from text, handling markdown code fence formatting.

        Removes markdown code fences (```json ... ```) and attempts to parse JSON.
        If standard parsing fails, searches for JSON object pattern within the text.

        Args:
            text (str): Text containing JSON, possibly wrapped in markdown code fences.

        Returns:
            dict: Parsed JSON object.

        Raises:
            ValueError: If no valid JSON can be extracted from the text.
        """
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match is None:
                raise ValueError("Model output did not contain JSON.")
            return json.loads(match.group(0))

    def generate(self, prompt: SummaryPrompt, max_new_tokens: int = 384) -> str:
        """Generate text from a prompt.

        Args:
            prompt (SummaryPrompt): Prompt payload for summary generation.
            max_new_tokens (int): Maximum number of tokens to generate. Defaults to 384.

        Returns:
            str: Raw generated text returned by the model.
        """
        self.logger.debug("Generating summary.")
        rendered_prompt = self.__build_prompt(prompt)
        result = self.__pipeline(
            rendered_prompt,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            return_full_text=False,
        )
        return result[0]["generated_text"].strip()

    def generate_many(
        self, prompts: list[SummaryPrompt], max_new_tokens: int = 384
    ) -> list[str]:
        """
        Generate text for multiple prompts.

        Args:
            prompts (list[SummaryPrompt]): Prompt payloads for summary generation.
            max_new_tokens (int): Maximum number of tokens to generate. Defaults to 384.

        Returns:
            list[str]: Raw generated text for each prompt.
        """
        self.logger.debug("Generating summaries in bulk.")
        rendered_prompts = [self.__build_prompt(prompt) for prompt in prompts]
        result = self.__pipeline(
            rendered_prompts,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            return_full_text=False,
        )
        return [entry[0]["generated_text"].strip() for entry in result]

    def generate_json(
        self,
        prompt: Union[SummaryPrompt, list[SummaryPrompt]],
        max_new_tokens: int = 384,
    ) -> Union[dict, list[dict]]:
        """
        Generate text from one or more prompts and parse the response as JSON.

        Args:
            prompt (SummaryPrompt or list[SummaryPrompt]): Prompt payload(s) for
                summary generation.
            max_new_tokens (int): Maximum number of tokens to generate. Defaults to 384.

        Returns:
            dict or list[dict]: Parsed JSON extracted from the generated text.
        """
        if isinstance(prompt, list):
            generated = self.generate_many(prompt, max_new_tokens=max_new_tokens)
            return [self.extract_json(text) for text in generated]

        return self.extract_json(self.generate(prompt, max_new_tokens=max_new_tokens))
