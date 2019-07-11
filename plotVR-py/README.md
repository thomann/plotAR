plotvr
=======

# plotVR - Walk Through your Data in Cardboard VR

This is a prototype to get your data into a Google Cardboard and navigate using the computer keyboard.

> **Disclaimer:** This is in Alpha stage, lot of things can go wrong.
> Data is transmitted in plain-text over you network and possibly further.
>
> Also the API is very instable.

* Free software: Affero GPL 3


Installation
------------

Prerequisites:
- Python 3 (we use Python 3.7)

It is recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```
The source statement has to be repeated whenever you open a new terminal.

Then install this version
```bash
pip install --upgrade git+https://github.com/thomann/plotvr#egg=plotvr&subdirectory=plotvr-py
```

If you want to use Jupyter, install it to the virtual environment:
```bash
pip install jupyterlab
```

### Development
To install this module in Dev-mode, i.e. change files and reload module:
```bash
git clone https://github.com/thomann/plotvr
cd plotvr/plotvr-py
```

It is recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

Install the version in edit mode:
```bash
pip install -e .
```

In Jupyter you can have reloaded code when you change the files as in:
```python
%load_ext autoreload
%autoreload 2
```

Usage
-----

```python
import plotvr

# connect to running elastic or else start an Open Source stack on your docker
from sklearn import datasets
iris = datasets.load_iris()

plotvr.plotvr(iris.data, iris.target)
```

In Jupyter you can open the controller:
```python
plotvr.controller()
```

Features
--------

* Pandas based pipeline
* Support for any extensions - now includes some for Regex, spaCy, VaderSentiment
* Write results to ElasticSearch
* Automatic Kibana dashboard generation
* Have Elastic started in Docker if it is not installed locally or remotely
* Apache License 2.0

Credits
-------

This package was created with [Cookiecutter](<https://github.com/audreyr/cookiecutter>) and the [`audreyr/cookiecutter-pypackage`]<https://github.com/audreyr/cookiecutter-pypackage> project template.
