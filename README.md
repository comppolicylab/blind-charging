# Blind Charging

[![Python Tests](https://github.com/stanford-policylab/blind-charging/actions/workflows/pytest.yaml/badge.svg?branch=main)](https://github.com/stanford-policylab/blind-charging/actions/workflows/pytest.yaml)
[![Python Lint](https://github.com/stanford-policylab/blind-charging/actions/workflows/pylint.yaml/badge.svg?branch=main)](https://github.com/stanford-policylab/blind-charging/actions/workflows/pylint.yaml)
[![Python Coverage](https://storage.googleapis.com/scpl-blind-charging/coverage/badge.svg)](https://storage.googleapis.com/scpl-blind-charging/coverage/www/index.html)

## Installation

The redaction algorithm can be installed using `pip` with the following command:

```bash
pip install blind_charging
```

## Basic Usage

The simplest usage of the blind charging algorithm looks like this:
```py
import blind_charging as bc

# Configure BlindCharging to use your locale.
bc.set_locale("Suffix County")

# Run the redaction algorithm passing in:
#   1) The input police narrative text;
#   2) A list of civilian (non-peace-officer) names referenced in the narrative;
#   3) A list of names of peace officers referenced in the narrative.
#
# This returns the redacted input narrative.
civilians = ["Sally Smith"]
officers = ["Sgt. John Jones"]
narrative = "Sgt. John Jones arrested Sally Smith (S1) in Parkside."
bc.redact(narrative, civilians, officers)
# '<Sergeant #1> arrested <(S1)> in <[neighborhood]>.'
```

## Locales

TODO(jnu): I'll add details about how to create and deploy the app with new locales.
Currently the locales for our pilot live in a separate (private) repo.

## Advanced Usage

### Generating annotations for custom display

The basic `redact` function applies redactions and returns the modified text.
If you would like to apply the redactions yourself (e.g., to present the report with stylized HTML formatting), you can run:

```py
annotations = bc.annotate(narrative, civilians, officers)
```

The annotations give character offsets within the text where the annotation should be applied, as well as additional semantic information you can use to annotate the text.

## Development

We use:
 - Python3 -- we target compatibility for all versions of Python starting with 3.8. (If we want to support Py3.7 we will need to downgrade Pandas, and probably other things.)
 - [poetry](https://python-poetry.org/) for managing packages and building the library
 - [pytest](https://docs.pytest.org/en/7.2.x/) for testing
 - [pre-commit](https://pre-commit.com/) for running formatters and linters
 - [black](https://github.com/psf/black) for code formatting
 - [isort](https://pycqa.github.io/isort/) for more code formatting
 - [flake8](https://flake8.pycqa.org/en/latest/) for linting

### Getting started
 - Ensure you have Python3 on your computer.
 - Install [`poetry`](https://python-poetry.org/docs/#installation) if needed
 - `poetry install --with dev` to install dependencies
 - `poetry run pre-commit install` to install git pre-commit hooks

### Running tests

Run all tests with pytest:
```zsh
poetry run pytest
```

### Building the library

TKTK workflow for automating this. `pytest build` works in the meantime.

# Contributors

This project was initially developed by a team at the Stanford Computational Policy Lab, including (in alphabetical order):
 - Alex Chohlas-Wood
 - Madison Coots
 - Sharad Goel
 - Amelia Goodman
 - Zhiyuan Jerry Lin
 - Joe Nudell
 - Julian Nyarko
 - Keniel Yao
