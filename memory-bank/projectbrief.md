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

## Roadmap

- A future version should include normalizing the cloud data platforms with an enterprise's SCIM (System for Cross-domain Identity Management) ACLs (Access Control Lists)
  - Start with a JSON inventory of the relevant ACLs the enterprise has already established.
  - The ACL names should be closely replicated for each platform component, such as IAM in AWS, and Security Groups in DBX.
  - When a user is removed from a SCIM ACL they should also be removed from the corresponding AWS IAM and DBX groups.
