To install dependencies: `pipenv install --dev`
To run the type checker: `pipenv run python -m mypy --exclude _samples .`
To run the linter: `pipenv run python -m flake8 .`
Example of running the translator on a file: `pipenv run python translator.py --ast-only -f _samples/1_global/simple.py`