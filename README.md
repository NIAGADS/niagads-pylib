# niagads-pylib

a collection of python packages, classes, and utility functions in support of NIAGADS projects

> This project is under-development and not recommended for third-party users

## Legacy Usage

> This project has been recently migrated to the Polylith Architecture.  Until the migration is complete, 
> the old package-based version can be used as follows:

```bash
pip3 install git+https://github.com/NIAGADS/niagads-pylib.git@package-architecture
```

## Documentation

github.io link TBA

## Python Version

* python 3.12+

## Usage - Packages

TBA

## Usage - Services

TBA

## Developers

The NIAGADS-pylib uses a [Polylith architecture](https://polylith.gitbook.io/polylith) managed with the [Python-polylith toolkit](https://davidvujic.github.io/python-polylith-docs/)

### Requirements

* Python >3.12, < 4.0
* pipx: <https://github.com/pypa/pipx>
* poetry package manager: <https://python-poetry.org/> (install w/pipx)
* Python Polylith tools: <https://davidvujic.github.io/python-polylith-docs/>
* toml-sort: <https://pypi.org/project/toml-sort/> (install w/pipx)

### Environment Setup

* install `pipx` (see dcoumentation linked above)
* install `poetry` using `pipx` (see documentation linked above)
* configure `poetry` to the `polylith` Python command line tools as per the tool documentation:

```bash
poetry self add poetry-multiproject-plugin
poetry self add poetry-polylith-plugin
```

Clone the repository and run the following the project root directory to set up the virtual environment and install the packages and third-party dependencies.

```bash
git clone https://github.com/NIAGADS/niagads-pylib
cd niagads-pylib
poetry install
```

> If working off a specific branch, checkout the branch before running `poetry install`.

### Polylith Architecture

Details TBA

### TOML organization

TODO: integrate in toml-sort in tag/release/publish github-action

While `poetry` helps sync the overall monorepo and sub-project dependencies, it does not organize the order of include statements or dependencies `.toml` files.  As the project grows this can make it difficult to at-a-glance inspect the the files and make manually adjustments.  The `toml-sort` Python command-line tool can be installed with `pipx` as follows:

```python
pipx install toml-sort
```

and then run to sort (alphabetize) the key-value pairs in the import blocks, as well as the array of `include` statements that link the Polylith bricks to the project.  Run `toml-sort` as follows (the `--sort-first` helps keep the basic order of the `.toml` file consistent).

```python
toml-sort --sort-first "project,tool,name,homepage,repository,packages" pyproject.toml
```

#### Hot Reloads for FastAPI

see <https://davidvujic.blogspot.com/2023/07/python-fastapi-microservices-with-polylith.html>

### VSCode Config

#### Recommended extensions

* [Microsoft Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
* [indent-rainbow](https://marketplace.visualstudio.com/items?itemName=oderwat.indent-rainbow)
* [autoDocstring](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring)
* [toml](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml)

> suggest configuring `autoDocstring` to use `google` style comment blocks

### Coding Conventions

Follow [PEP 8](https://peps.python.org/pep-0008/) coding standards.

#### Naming

* `file names` and `directories` should be in [snake_case](https://www.theserverside.com/definition/Snake-case)
* `function` and 'variable' names should be in `snake_case`
* `class` names should be in [UpperCamelCase](https://www.techtarget.com/whatis/definition/CamelCase#:~:text=CamelCase%20is%20a%20way%20to,humps%20on%20a%20camel%27s%20back.)
* `constants` should be in `UPPER_SNAKE_CASE`

#### Code Documentation

All functions, classes and packages should have a doc-string.  For non-inuitive or complex functions, please provide a `summary` description, a list of `args`, a description of the `return value`, and any `raised exceptions`.  For simple functions (e.g., member `getters` and `setters`, no documentation is need or a simple `summary` doc string will suffice)

* Use [Google style documentation](https://google.github.io/styleguide/pyguide.html#docstrings)

> NOTE: you **MUST** give credit when pulling code from a third-party (e.g., StackOverflow, GitHub) or when generated using a chatbot (e.g., ChatGPT/Claude).  Please include the URL or link to the specific response (each StackOverflow response has a _share_ link) in your documentation.
> for example: [niagads.utils.string.is_balanced](https://github.com/NIAGADS/niagads-pylib/blob/34f505b49332e95b14bdd9074ad4e5534d70bd3f/components/niagads/utils/string.py#L329C1-L351C28), 
> or [niagads.utils.list.chunker](https://github.com/NIAGADS/niagads-pylib/blob/34f505b49332e95b14bdd9074ad4e5534d70bd3f/components/niagads/utils/list.py#L66C1-L81C28)

#### Logging

Please use `logging` to log script progress and debug statements. Details coming soon.

#### Classes

* When definining `classes`, try to stick to the principles of `Object Oriented Programming`: `Encapsulation, Data Abstraction, Polymorphism and Inheritence`.  

> Especially `Encapsulation` (a class's variables are hidden from other classes and can only be accessed by the methods of the class in which they are found):

* all `class variables` should be `private` (`protected` if class using Inheritence and class has children) 
  * `private`: variable only accessible within the class
    * naming: starts with `__` (double underscore; e.g., `__size`)
  * `protected`: variable accesesible within class and any child classes
    * naming: starts with `_` (underscore; e.g., `_size`)

  * to access the member variable `__size`, there should be a function `set_size(self, size)` and `get_size(self)` or `size(self)`.  Python `@property` decorators are also acceptable.
  
* when creating `class methods` consider usage of functions and make functions `private` or `protected` if they should not be directly accessed by the user (i.e., only used internally by the class) by prefixing with `__` or `_` as needed

* all classes should have a `public` `logger` member variable
* 
* all classes should have a `protected` `_debug` and `_verbose` member variable

* override the `__str__` [dunder method](https://mathspp.com/blog/pydonts/dunder-methods) for the class so that users can debug or write class state as output (i.e., convert class to string)


#### Other

* use [type hints](https://docs.python.org/3/library/typing.html) when possible help the `Pylance` (the Python interpreter) provide better autocompletion examples

* use `enums` to define variables limited to controlled vocabularies
