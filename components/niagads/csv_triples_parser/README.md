<!-- markdownlint-disable -->

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `core.py`






---

## <kbd>class</kbd> `CSVTriplesParser`




<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L17"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(
    file: str,
    definitionFile: str = None,
    parserType: RDFTripleType = <RDFTripleType.SEMANTIC: 'SEMANTIC'>,
    ontology: str = 'niagads'
)
```








---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `add_owl_class`

```python
add_owl_class(label: str)
```

create and add a new class node  node is of type OWL.Class  node is subClassOf OWL.Thing  node label = value  node definition = self.__defintions[label] 



**Args:**
 
 - <b>`label`</b> (str):  the label of the node 



**Returns:**
 
 - <b>`URIRef `</b>:  the URIRef for the node 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L42"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_defintions`

```python
get_defintions()
```

Return the definition map 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L100"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `parse`

```python
parse(header: bool = False)
```

parse the triples file 



**Args:**
 
 - <b>`header`</b> (bool, optional):  set to `True` if file contains header row to be ignored. Defaults to False. 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L80"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `parse_class_hierarchy_triple`

```python
parse_class_hierarchy_triple(triple: List[str])
```

assumes a list of values contains a triple of: class <-> subclass <-> term 

creates a node each for class, subclass, and term creates the following relationships  subclass is a subClassOf class  term is a subClassOf subclass 



**Args:**
 
 - <b>`values`</b> (List[str]):  list containing the class <-> subclass <-> term triple 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L46"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `parse_semantic_triple`

```python
parse_semantic_triple(triple: List[str])
```

Parse a subject <-> predicate <-> object triple 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L136"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `to_owl`

```python
to_owl(file: str = None, pretty: bool = False)
```

Convert to owl format; wrapper for `to_xml`, just ensures .owl extension on file name 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L119"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `to_ttl`

```python
to_ttl(file: str = None)
```

Convert to turtle format see <https://www.w3.org/TR/turtle/> for specification 

if `file` is provided, will write the turtle formatted graph to file otherwise returns the turtle object 



**Args:**
 
 - <b>`file`</b> (str, optional):  write output to specified file. Defaults to None. 



**Returns:**
 
 - <b>`str`</b>:  formatted turtle (ttl) string 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/csv_triples_parser/core.py#L142"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `to_xml`

```python
to_xml(file: str = None, pretty: bool = False)
```

Convert to xml format 



**Args:**
 
 - <b>`file`</b> (str, optional):   write output to specified file. Defaults to None. 
 - <b>`pretty`</b> (bool, optional):  pretty print the xml. Defaults to False. 



**Returns:**
 
 - <b>`str`</b>:  formatted xml string 


---

## <kbd>class</kbd> `RDFTripleType`










---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
