# Skills Project — AI Operating System for Developers

## Overview
This is a collection of Claude Code skills designed to build an **AI Operating System** for developers at **Colgate**. The goal is to automate repetitive workflows so developers can work faster and focus on high-value tasks.

## Context
- **Company**: Colgate
- **IDE**: Windsurf
- **Platform**: Shopify ecommerce theme development
- **Tooling**: Jira, Apiiro, SonarQube, AQA/UsableNet (accessibility), and more
- **Purpose**: Create reusable, composable skills that other developers can plug into their Claude Code workflow — forming an automation layer ("AI OS") across the dev lifecycle

## Existing Skills
- **apiiro-fix** — Remediate Apiiro security findings automatically
- **aqa-usablenet** — Accessibility testing and fixes via AQA API v3.1
- **sonarqube-fix** — Fix SonarQube code quality and security issues
- **fix-errors** — Auto-fix build/runtime errors
- **triage-errors** — Triage and categorize errors for prioritization
- **package-version-update** — Update package versions across the project

## Conventions
- Each skill lives in its own directory with a `SKILL.md`
- Skills should use REST APIs directly (not CLIs) when possible
- Skills should be idempotent and safe to re-run
- Keep skills focused on a single responsibility
- Never use Claude username in git commits
