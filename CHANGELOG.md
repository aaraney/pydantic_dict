# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.2] - 2023-06-28

### Added

- `Unset` marker type used to "mark" that an optional model field is by default
  not set but also not required to construct the model (#1).
- Added support for `Unset` marker type on `BaseModelDict` (#1).

## [0.0.1] - 2023-06-21

### Added

- Initial release of `pydantic_dict` -- A pydantic model subclass that
  implements Python's built-in dictionary interface.
