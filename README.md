# niagads-pylib

a collection of python packages, classes, and utility functions in support of NIAGADS projects

# Documentation

see https://niagads.github.io/niagads-pylib

# Requirements

* python 3.10+

# Installation

> NOTE: add the `--user` flag to the `pip3` or `setup.py` calls to install as a `user` or `local` package
> add `#branch-name` to the end of the URL to install from a specific branch

## `pip3` installation direct from GitHub:

* latest stable / `main` branch

```bash
pip3 install git+https://github.com/NIAGADS/niagads-pylib.git
```
* other branch
```bash
pip3 install git+https://github.com/NIAGADS/niagads-pylib.git#branch-name
```

## `python3 setup.py` from local working version
```bash
git clone https://github.com/NIAGADS/niagads-pylib.git
cd niagads-pylib
python3 -m pip install .
```

## docker 

* Requires `docker` or `docker desktop`

> NOTE: This is for **_`NIAGADS organization` members only_** at this time

If a member of NIAGADS, make a request to `Emily G` or `Otto V` to be added to the NIAGADS GitHub organization, and to be given access to the `Docker Team` for read access to the `NIAGADS/docker-repo`. Next:

```bash 
git clone https://github.com/NIAGADS/docker-repo.git
docker build --build-arg GID=$GID --pull --rm -f "docker-repo/dev-environments/pylib/Dockerfile" -t pylib:latest "docker-repo/dev-environments/pylib
```

> `${GID}` is your group_id; this is for permissions if you need to run a script that requires mounting a volume and writing to the host (defaults to `1001`)

> use the `--build-arg` `PYLIB_SOURCE` to override the `GitHub` target (e.g., use your own fork or a branch other than `main`)

Example `docker` usage will be provided in the `README` for the `NIAGADS/docker-repo`

# Contributing

## Suggested working environment

* [vscode](https://code.visualstudio.com/)

* VSCode extensions:
  * [Microsoft Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
  * [indent-rainbow](https://marketplace.visualstudio.com/items?itemName=oderwat.indent-rainbow)
  * [autoDocstring](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring)

> suggest configuring `autoDocstring` to use `google` style comment blocks

* create a python [venv](https://docs.python.org/3/library/venv.html) to facilitate testing scripts

## Standard Operating Procedure

> More details coming soon

* create your own fork 
* do a local test merge & sync your fork with `NIAGADS/pylib#integration` to resolve conflicts/changes since you started working on your fork
* make `pull request`, using the `integration` branch as the base for comparison to submit contribution

## Coding Conventions

### Naming

* `file names` and `directories` should be in [snake_case](https://www.theserverside.com/definition/Snake-case)
* `function` names should be in `snake_case`
* `variable` names should be in [lowerCamelCase](https://www.techtarget.com/whatis/definition/CamelCase#:~:text=CamelCase%20is%20a%20way%20to,humps%20on%20a%20camel%27s%20back.)
* `class` names should be in [UpperCamelCase](https://www.techtarget.com/whatis/definition/CamelCase#:~:text=CamelCase%20is%20a%20way%20to,humps%20on%20a%20camel%27s%20back.)
* `constants` should be in `UPPER_SNAKE_CASE`

### Documentation

All functions, classes and packages should have a doc-string.  For non-inuitive or complex functions, please provide a `summary` description, a list of `args`, a description of the `return value`, and any `raised exceptions`.  For simple functions (e.g., member `getters` and `setters`, no documentation is need or a simple `summary` doc string will suffice)

> NOTE: you **MUST** give credit when pulling code from a third-party (e.g., StackOverflow, GitHub).  Please include the URL or link to the specific response (each StackOverflow response has a _share_ link) in your documentation.
> for example: [niagads.utils.string.is_balanced](https://niagads.github.io/niagads-pylib/_modules/niagads/utils/string.html#is_balanced), 
> or [niagads.utils.list.chunker](https://niagads.github.io/niagads-pylib/_modules/niagads/utils/list.html#chunker)

### Logging

Please use `logging` to log script progress and debug statements. Details coming soon.

### Classes
* When definining `classes`, try to stick to the principles of `Object Oriented Programming`: `Encapsulation, Data Abstraction, Polymorphism and Inheritence`.  

> Especially `Encapsulation` (a class's variables are hidden from other classes and can only be accessed by the methods of the class in which they are found):

* all `class variables` should be `private` (`protected` if class using Inheritence and class has children) 
  * `private`: variable only accessible within the class
    * naming: starts with `__` (double underscore; e.g., `__size`)
  * `protected`: variable accesesible within class and any child classes
    * naming: starts with `_` (underscore; e.g., `_size`)

* `getters` and `setters` methods should be defined to set and access (get) member variables that the user may need to access directly
  * to access the member variable `__size`, there should be a function `set_size(self, size)` and `get_size(self)` or `size(self)`
  
* when creating `class methods` consider usage of functions and make functions `private` or `protected` if they should not be directly accessed by the user (i.e., only used internally by the class) by prefixing with `__` or `_` as needed

* all classes should have a `public` `logger` member variable
  
* all classes should have a `protected` `_debug` member variable

* override the `__str__` [dunder method](https://mathspp.com/blog/pydonts/dunder-methods) for the class so that users can debug or write class state as output (i.e., convert class to string)



### Scripts

Executable scripts can be added to the `scripts` directory. `setup.py` will also need to be updated.  Details coming soon.

### Other

* use [type hints](https://docs.python.org/3/library/typing.html) when possible help the `Pylance` (the Python interpreter) provide better autocompletion examples

* use `enums` to define variables limited to controlled vocabularies (see the [enums utilities](niagads/utils/enums.py) and the [api_wrapper constants](niagads/api_wrapper/constants.py) for examples)

