from setuptools import setup
import re

requirements = []
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

version = author = repo = ""
with open('source/__init__.py') as f:
    src = f.read()
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', src, re.MULTILINE).group(1)
    author  = re.search(r'^__author__\s*=\s*[\'"]([^\'"]*)[\'"]',  src, re.MULTILINE).group(1)
    repo    = re.search(r'^__repo__\s*=\s*[\'"]([^\'"]*)[\'"]',    src, re.MULTILINE).group(1)

if not version or version == "dev":
    version = "0.0.0"

readme = ""
with open('README.md') as f:
    readme = f.read()

setup(
    name="Saruman",
    version=version,
    author=author,
    url=repo,
    license="GPLv3",
    description="A discord bot for scheduling raids."
    long_description=readme,
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.8',
)
