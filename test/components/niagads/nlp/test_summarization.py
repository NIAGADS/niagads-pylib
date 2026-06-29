from pathlib import Path
import sys

import pytest
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


ROOT = Path(__file__).resolve().parents[4]
for package_root in [ROOT / "components", ROOT / "bases"]:
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)


from niagads.nlp.llm_types import LLM
from niagads.nlp.models import SummaryPrompt
from niagads.nlp.summarization import TextSummaryGenerator


TEST_MODEL_NAME = "sshleifer/tiny-gpt2"
CHAT_TEMPLATE = """{% for message in messages %}{{ message['role'] }}: {{ message['content'] }}\n{% endfor %}{% if add_generation_prompt %}assistant: {% endif %}"""


@pytest.fixture(scope="module")
def tiny_generation_pipeline():
    try:
        tokenizer = AutoTokenizer.from_pretrained(TEST_MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(TEST_MODEL_NAME)
    except Exception as err:
        pytest.skip(f"Unable to load lightweight HF test model `{TEST_MODEL_NAME}`: {err}")

    tokenizer.chat_template = CHAT_TEMPLATE
    return pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
    )


@pytest.fixture
def summary_prompt():
    return SummaryPrompt(
        system_prompt="Return a short JSON object with key summary_text.",
        user_prompt='Return {"summary_text": "test"}',
    )


def test_render_prompt_uses_chat_template(monkeypatch, tiny_generation_pipeline, summary_prompt):
    monkeypatch.setattr(
        TextSummaryGenerator,
        "_TextSummaryGenerator__initialize_pipeline",
        staticmethod(lambda model: tiny_generation_pipeline),
    )
    generator = TextSummaryGenerator(LLM.BART_LARGE_CNN)

    rendered_prompt = generator.render_prompt(summary_prompt)

    assert "system:" in rendered_prompt
    assert "user:" in rendered_prompt
    assert "assistant:" in rendered_prompt


def test_generate_returns_text(monkeypatch, tiny_generation_pipeline, summary_prompt):
    monkeypatch.setattr(
        TextSummaryGenerator,
        "_TextSummaryGenerator__initialize_pipeline",
        staticmethod(lambda model: tiny_generation_pipeline),
    )
    generator = TextSummaryGenerator(LLM.BART_LARGE_CNN)

    generated_text = generator.generate(summary_prompt, max_new_tokens=12)

    assert isinstance(generated_text, str)
    assert generated_text.strip()


def test_generate_json_uses_extract_json(monkeypatch):
    generator = TextSummaryGenerator.__new__(TextSummaryGenerator)
    monkeypatch.setattr(
        generator,
        "generate",
        lambda prompt, max_new_tokens=384: '```json\n{"summary_text": "test"}\n```',
    )

    parsed = generator.generate_json(
        SummaryPrompt(system_prompt="system", user_prompt="user")
    )

    assert parsed == {"summary_text": "test"}
