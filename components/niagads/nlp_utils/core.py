import spacy
from typing import List


def segment_sentences(text: str) -> List[str]:
    """
    Use spaCy to segment text into sentences.
    Returns a list of sentence strings.
    """
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]
