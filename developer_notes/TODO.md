# Classification

* investigate `AutoModelForSequenceClassification` for doing  classification tasks w/BERT.  Loads the BERT model + additional embeddings that map BERT output to classification labels

* `AutoModelForCausalLM` improves NL representation of response

usage eg:

```python
AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1", device_map="auto")
```