# Shopify Admin API & CLI — Common Patterns

Shared reference for skills and GitHub Actions that interact with Shopify stores.

## Two Approaches

1. **Shopify CLI** (`shopify theme push/pull`) — used by GitHub Actions and deploy-release
2. **Admin REST API** — used when CLI is unavailable or finer control is needed

For skills running in Windsurf/Claude Code, prefer the CLI. For GitHub Actions, both work depending on auth setup.

## Environment Variables

### For Skills (multi-store via JSON)

| Variable | Example |
|----------|---------|
| `SHOPIFY_STORES_JSON` | `[{"name":"US","url":"store-us.myshopify.com","token":"shpat_xxx"},{"name":"CA","url":"store-ca.myshopify.com","token":"shpat_xxx"}]` |

### For GitHub Actions (as secrets)

| Secret | Purpose |
|--------|---------|
| `SHOPIFY_STORES_JSON` | Same JSON array as above |
| `SHOPIFY_CLI_THEME_TOKEN` | Theme Access password (if using CLI auth) |

---

## Shopify CLI — Theme Operations

### Push theme to a store (unpublished)

```bash
shopify theme push \
  --store="$STORE_URL" \
  --password="$STORE_TOKEN" \
  --unpublished \
  --theme="$THEME_NAME" \
  --ignore=config/settings_data.json
```

Flags:
- `--unpublished` — creates a new unpublished theme (safe for preview)
- `--theme="name"` — target an existing theme by name (for updates)
- `--ignore=config/settings_data.json` — protect merchant customizations
- `--nodelete` — don't delete remote files that don't exist locally
- `--allow-live` — required to push to the live theme (use with caution)

### List themes

```bash
shopify theme list --store="$STORE_URL" --password="$STORE_TOKEN"
```

### Delete a theme

```bash
shopify theme delete --theme="$THEME_ID" --store="$STORE_URL" --password="$STORE_TOKEN" --force
```

### Pull theme (download)

```bash
shopify theme pull --store="$STORE_URL" --password="$STORE_TOKEN" --theme="$THEME_ID"
```

---

## Admin REST API — Theme Operations

Base URL: `https://{store_url}/admin/api/2024-01`
Auth header: `X-Shopify-Access-Token: {access_token}`

### List themes

```bash
curl -s \
  "https://$STORE_URL/admin/api/2024-01/themes.json" \
  -H "X-Shopify-Access-Token: $STORE_TOKEN"
```

Response: `{"themes": [{"id": 123, "name": "Dawn", "role": "main"}, {"id": 456, "name": "preview-pr-42", "role": "unpublished"}]}`

Roles: `main` (live), `unpublished`, `demo`

### Create theme

```bash
curl -s -X POST \
  "https://$STORE_URL/admin/api/2024-01/themes.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: $STORE_TOKEN" \
  -d '{"theme": {"name": "preview-pr-42", "role": "unpublished"}}'
```

### Delete theme

```bash
curl -s -X DELETE \
  "https://$STORE_URL/admin/api/2024-01/themes/$THEME_ID.json" \
  -H "X-Shopify-Access-Token: $STORE_TOKEN"
```

### Publish theme (make live)

```bash
curl -s -X PUT \
  "https://$STORE_URL/admin/api/2024-01/themes/$THEME_ID.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: $STORE_TOKEN" \
  -d '{"theme": {"role": "main"}}'
```

**Warning:** This makes the theme live immediately. The deploy-release skill deploys as unpublished — business publishes manually.

---

## Multi-Store Iteration Pattern

Used by deploy-release skill and GitHub Actions to loop over all stores:

### In bash (skills)

```bash
echo "$SHOPIFY_STORES_JSON" | jq -c '.[]' | while read -r store; do
  STORE_NAME=$(echo "$store" | jq -r '.name')
  STORE_URL=$(echo "$store" | jq -r '.url')
  STORE_TOKEN=$(echo "$store" | jq -r '.token')

  echo "Deploying to $STORE_NAME ($STORE_URL)..."
  shopify theme push \
    --store="$STORE_URL" \
    --password="$STORE_TOKEN" \
    --unpublished \
    --theme="Release v1.3.0" \
    --ignore=config/settings_data.json

  if [ $? -eq 0 ]; then
    echo "  ✓ $STORE_NAME deployed successfully"
  else
    echo "  ✗ $STORE_NAME deployment failed"
  fi
done
```

### In GitHub Actions (matrix strategy)

```yaml
jobs:
  deploy:
    strategy:
      matrix:
        store: ${{ fromJson(secrets.SHOPIFY_STORES_JSON) }}
    steps:
      - uses: actions/checkout@v4
      - uses: shopify/cli-action@v1
      - run: |
          shopify theme push \
            --store="${{ matrix.store.url }}" \
            --password="${{ matrix.store.token }}" \
            --unpublished \
            --theme="preview-pr-${{ github.event.pull_request.number }}"
```

---

## Theme Naming Conventions

| Context | Theme Name | Example |
|---------|------------|---------|
| PR preview | `preview-pr-{PR_NUMBER}` | `preview-pr-42` |
| Release preview | `release-preview-{VERSION}` | `release-preview-v1.3.0` |
| Release deploy | `Release {VERSION}` | `Release v1.3.0` |

These naming conventions are used to find and clean up themes in the pr-cleanup and release-cleanup actions.

## Finding a Theme by Name

```bash
THEME_ID=$(curl -s \
  "https://$STORE_URL/admin/api/2024-01/themes.json" \
  -H "X-Shopify-Access-Token: $STORE_TOKEN" \
  | jq -r '.themes[] | select(.name == "preview-pr-42") | .id')
```
