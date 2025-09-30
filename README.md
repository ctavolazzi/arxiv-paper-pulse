# arxiv-paper-pulse

A Python package that fetches recent AI and physics papers from arXiv and summarizes their abstracts using a local Ollama model.

## Features

- **Fetch Papers:** Uses [arxiv.py](https://github.com/lukasschwab/arxiv.py) to query arXiv for AI and physics papers.
- **Local Summarization:** Runs the paper abstract through your local Ollama instance.
- **JSON Storage:** Summaries are stored in a JSON file.
- **CLI and Library Usage:** Run it from the command line or import it in your projects.
- **Scheduling:** Optionally schedule periodic runs.

## Installation

Clone the repository, then install locally:

```bash
pip install .
