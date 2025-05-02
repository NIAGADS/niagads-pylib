# TODOs

## Training Set Generation

* find articles
* filter articles to match existing dataset properties

Please do the following and then make a pull-request so we can close the branch and move on to a new task

> **Your choice: explore NCBI E-Utils to test if fetches are faster w/out the python library overhead**

> My guess yes; I bet the python library uses `requests` which is very slow compared to `aiohttp`
  
### 1. Find articles within a time range that match MeSH terms

* extract PubMed ID, title, abstract, journal name, publication date, MeSH terms (in case user wants to do a secondary filter)
* exclude preprints
* add filter for Open Access only
* **result should be JSON keyed on pubmed ids**
* remove any references to AD -> no reason why this can't be generic
* encapsulate in a class: PubmedTrainingSetGenerator
* but also have a main so that it can be called as a script or imported as a package
* arguments:
  * meshTerms: list of MeSH terms; limit to a reasonable number like max 5
  * yearStart, yearEnd, or dateRange: e.g., yearStart:yearEnd
  * ncbiApiKey
  * openAccessOnly boolean
  * limit or firstN (i.e., max number of matches to retrieve)


> A note: do not search Abstracts for keywords as AD  being in an abstract could just be a reference (e.g., Parkinson's, as with AD...).  Search MeSH terms in MeSH terms only

> A note: make members protected (one _) instead of private

```python

class PubmedTrainingSetGenerator:

    def __init__(ncbiApiKey:str = None):
        """ initialize generator """
    
        self.__ncbi_api_key = self.__validate_api_key()
        self.__training_set = None


    # only functions necessary for generating and returning the training dataset
    def __valdiate_api_key():
        # validate/set api key if key is None, try to pull from os.environ; 
        # if it doesn't exist you can choose to either fail or give warning that it will run slow and add wait between requests
        pass 

    def add_filter():
        # would it work to create a generic `add_filter` member function that 
        # takes a field and value? (e.g., add_filter(`MeSH Terms`, <list_of_mesh_terms>))
        # if you go this route, create an Enum of allowable filters
        # or will we need field specific setters?
        pass

    def set_limit():
        pass

    def set_open_access_only():
        pass

    def as_dict()
        pass

    def as_csv():
        """ convert to csv and return """
        pass

    # functions for extracting subsets
    def get_pubmed_ids():
        pass

    def get_journals():
        pass


    def extract_pdfs(targetDir: str):
        """ 
        target directory needs to be a full path or have to assume cwd()? choose how to handle
        don't forget to give warning if --openAccessOnly is False
        rename? to pubmed_id.pdf 
        add "pdf": <full path to pdf> to the result JSON (right now self.__training_set)
        """ 
        pass

    def run():
        """ run generator and save JSON result to self.__training_set.  This will let us encapsulate getters """
        pass


async def main(**kwargs):
    # initialize the class
    # add filters and limits (e.g., number of )
    # run the generator
    # pipe JSON output to stdout
    pass

if __name__ == "__main__":
    # parse the args here b/c they are only relevant in this case
    import argparse
    ...
    asyncio.run(main(**vars(args)))
```

### 2. PubMed Analyzer

Restructure into encapsulated class as outlined above.  This should do exactly one task: take in a list of pubmed ids and summarize:

* distribution over the years
* journals
* MeSH terms (can also calcualte distribution; i.e. count of articles per term;  maybe interesting)

Remove or set aside anything in the code that does more than this.

### 3. Filter to match an existing dataset in terms of journals, distribution over time, and possible MeSH terms

Filter 1 by 2; let's discuss this step next week.

## Classification - EGA will start on this for next week

Use LangChain

* compare Claude and OpenAI

### 


* investigate `AutoModelForSequenceClassification` for doing  classification tasks w/BERT.  Loads the BERT model + additional embeddings that map BERT output to classification labels

* `AutoModelForCausalLM` improves NL representation of response

usage eg:

```python
AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1", device_map="auto")
```