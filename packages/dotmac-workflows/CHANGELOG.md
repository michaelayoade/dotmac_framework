# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-XX

### Added
- Initial release of dotmac-workflows
- Base `Workflow` class with step execution
- `WorkflowStatus` and `WorkflowResult` types
- Approval workflow support with pause/resume
- Rollback on failure configuration
- Callback system for workflow events
- Pluggable persistence interface
- Comprehensive type hints and async support
- Full test suite with 100% coverage