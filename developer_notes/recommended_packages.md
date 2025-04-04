# Recommended Python Packages

## Requirements

Python 3.12+

## MetaPub

Metapub is a Python library that provides python objects fetched via eutils that represent Pubmed papers and concepts found within the NCBI databases.

<https://pypi.org/project/metapub/>

* example usage (from contributor) on how to get full text: <https://stackoverflow.com/a/78733212>

## AIOHTTP

Python's `requests` library is slow, obsolete, and does not support async

Use instead [AIOHTTP](https://docs.aiohttp.org/en/stable/), an Asynchronous HTTP Client/Server for asyncio and Python.

## spaCy

spaCy is a modern natural language processing library that provides pre-trained models for various languages. We use it for word embeddings and semantic similarity calculations.

<https://spacy.io/>

## NLTK

The Natural Language Toolkit (NLTK) is a platform for building Python programs to work with human language data. We use it for text tokenization and stopword removal.

<https://www.nltk.org/>

## scikit-learn

scikit-learn is a machine learning library for Python. We use it for calculating cosine similarity between word embeddings.

<https://scikit-learn.org/>


### Learning Topics

* connection pooling
  * <https://medium.com/@digi0ps/connection-pooling-what-and-why-8d659e1530f9>
  * <https://devblogs.microsoft.com/premier-developer/the-art-of-http-connection-pooling-how-to-optimize-your-connections-for-peak-performance/>
* `asyncio`: <https://docs.python.org/3/library/asyncio.html>