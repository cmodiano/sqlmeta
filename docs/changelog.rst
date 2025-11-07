Changelog
=========

All notable changes to this project will be documented in this file.

Version 0.1.0 (2024-11-06)
--------------------------

Initial release

Features
~~~~~~~~

* Core schema representation with dialect-agnostic SQL objects
* Support for tables, views, procedures, triggers, sequences, indexes, and more
* Schema comparison and drift detection with type normalization
* SQLAlchemy adapter for bidirectional conversion
* Pydantic adapter for model generation
* Alembic adapter for migration generation
* Support for PostgreSQL, MySQL, Oracle, and SQL Server
* Full type hints and documentation
* Zero required dependencies (adapters are optional)

Supported Objects
~~~~~~~~~~~~~~~~~

* Tables with columns, constraints, and partitions
* Views and materialized views
* Stored procedures and functions
* Triggers
* Sequences
* Indexes
* PostgreSQL extensions, foreign data wrappers, and foreign servers
* Oracle packages, database links, and synonyms
* SQL Server linked servers and temporal tables
* MySQL events and storage engines
* User-defined types

Future Releases
---------------

See the project roadmap in README.md for planned features.
