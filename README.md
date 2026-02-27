# Fusion CDT community reading list
A collection of useful resources related to plasma physics, material science and fusion power created by students on the [EPSRC CDT in Fusion Power](https://fusion-cdt.ac.uk/). 

> [!WARNING]
> This is a work-in-progress.

## Build locally
If you'd like to build the site locally, first clone the repository:
```sh
git clone git@github.com:Fusion-CDT/fusion-cdt-community-reading-list.git
```

Then change to the project directory:
```sh
cd fusion-cdt-community-reading-list
```

Install dependencies. If you have [`uv`](https://docs.astral.sh/uv/) installed:
```sh
uv sync && source .venv/bin/activate
```

Otherwise, using `pip`:
```sh
python -m venv .venv && source .venv/bin/activate
pip install .
```

Build site
```sh
zensical serve
```

Open the site using [http://localhost:8000](http://localhost:8000)

## Checking out other branches
If you'd like to check out the 'flat' structure, run:
```sh
git switch flat-structure
```

Then re-build the site with
```sh
zensical serve
```
