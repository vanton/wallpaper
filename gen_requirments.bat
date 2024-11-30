:: cspell:words setuptools
pip list -l --exclude pip --exclude setuptools --exclude wheel --not-required --format freeze > requirements.txt
