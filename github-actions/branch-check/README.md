# Branch Name Check

Validates that PR branch names contain a Jira ticket ID (e.g., `ENG-123`).

## Trigger
- Pull request opened or updated targeting `dev`

## What it does
- Checks branch name matches pattern `[A-Z]+-[0-9]+`
- Allows `release/*` and `main` branches without ticket ID
- Fails the check if no ticket ID found, with examples of correct format

## Setup
1. Copy `workflow.yml` to `.github/workflows/branch-check.yml` in your theme repo
2. No secrets required

## Customization
- Change `branches: [dev]` to match your integration branch name
