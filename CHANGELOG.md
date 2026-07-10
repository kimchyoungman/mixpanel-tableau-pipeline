# Changelog

All notable changes to this project will be documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
intends to use [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Python package metadata and optional Tableau, GCS, and development extras.
- Automated tests and CI for Python 3.11 and 3.12.
- Docker build-context protection and non-root container execution.
- GitHub Actions artifact retention when Tableau publishing is disabled.

### Changed

- Empty exports now produce a valid empty Hyper extract.
- GCS state failures now stop the pipeline instead of being treated as missing
  state or successful persistence.
- Google Cloud builds now target Artifact Registry.
