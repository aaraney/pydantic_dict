# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.3] - 2023-06-30

## Changes

- Pin `pydantic<2`. [Pydantic 2](https://pypi.org/project/pydantic/2.0/) was
  released today. This major version release introduces some breaking changes
  that will need to be addressed. Unlike pydantic, hopefully we can support v1
  and v2 without breaking our api.

## [0.0.2] - 2023-06-28

### Added

- `Unset` marker type used to "mark" that an optional model field is by default
  not set but also not required to construct the model (#1).
- Added support for `Unset` marker type on `BaseModelDict` (#1).

## [0.0.1] - 2023-06-21

### Added

- Initial release of `pydantic_dict` -- A pydantic model subclass that
  implements Python's built-in dictionary interface.
