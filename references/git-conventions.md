# Git Conventions

Shared branch naming, commit format, and PR templates used across all skills.

## Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<TICKET_KEY>-<slug>` | `feature/ENG-123-add-cart-drawer` |
| Bug fix | `bugfix/<TICKET_KEY>-<slug>` | `bugfix/ENG-456-fix-null-price` |
| Hotfix | `hotfix/<TICKET_KEY>-<slug>` | `hotfix/ENG-789-fix-checkout-crash` |
| Release | `release/<version>` | `release/v1.3.0` |
| Error fix | `fix/error-<TICKET_KEY>-<date>` | `fix/error-ENG-100-2026-03-29` |

Slug rules:
- Lowercase, hyphens only (no underscores or spaces)
- Max 50 chars for the slug portion
- Derived from ticket summary: "Add Cart Drawer" → `add-cart-drawer`

## Commit Message Format

```
type(scope): short description [TICKET_KEY]

Optional body explaining why, not what.
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`, `perf`

Examples:
```
feat(cart): add drawer component [ENG-123]
fix(checkout): handle null price on line items [ENG-456]
chore(release): bump version to v1.3.0
```

## PR Template

```markdown
## Summary

<1-3 sentences describing what and why>

**Jira:** [<TICKET_KEY>]($JIRA_URL/browse/<TICKET_KEY>)

## Changes

- <bulleted list of key changes>

## Test Plan

- [ ] Build passes
- [ ] Tests pass
- [ ] <domain-specific checks>

## Screenshots

<if applicable>
```

## Branch Strategy

```
main ←── production-ready code, tagged releases
  ↑
  │ merge (release branch)
  │
release/v1.3.0 ←── cut from dev, tested, then merged to main
  ↑
  │ cut from dev
  │
dev ←── integration branch, PRs target here
  ↑
  │ merge (feature PRs)
  │
feature/ENG-123-* ←── individual work branches
```

Hotfixes branch from `main` and merge back to both `main` and `dev`.
