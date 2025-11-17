# Project Brief

The goal of this project is to provide a CLI-based means of establishing and governing naming conventions for an Amazon Web Services (AWS) and Databricks (DBX) enterprise data platform.

## Core Purpose

Plan and CRUD resource names locally with a JSON file, then in AWS & DBX to ensure continuity across the platform.

## System Overview

- **Project Structure**:

  - /docs contain 1 naming guide per major cloud platform, AWS, DBX.
  - /examples/blueprints contain examples of what a blueprint should look like.
  - src/data-platform-naming contains
    - platform naming conventions, constants, and validators
    - cli source code
    - crud/ contains Python for platform operations
    - plan/ contains Python for blueprints
  - tests/ contains unit tests of all functionality
