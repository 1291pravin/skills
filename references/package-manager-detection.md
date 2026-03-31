# Package Manager Detection

Shared reference for detecting and using the project's package manager. Used by multiple skills.

## Detection Logic

Check in this order (first match wins):

1. `package.json` → `packageManager` field (e.g., `"packageManager": "pnpm@9.0.0"`)
2. `bun.lockb` or `bun.lock` exists → **bun**
3. `pnpm-lock.yaml` exists → **pnpm**
4. `yarn.lock` exists → **yarn**
   - If `.yarnrc.yml` also exists or `packageManager` contains `yarn@4` or higher → **Yarn 4 (Berry)**
   - Otherwise → **Yarn Classic (v1)**
5. `package-lock.json` exists → **npm**

If no lock file is found, ask the user which package manager to use.

## Command Reference

| Action | npm | yarn v1 | yarn v4 | pnpm | bun |
|--------|-----|---------|---------|------|-----|
| Install deps | `npm ci` | `yarn install --frozen-lockfile` | `yarn install --immutable` | `pnpm install --frozen-lockfile` | `bun install --frozen-lockfile` |
| Update pkg | `npm install <pkg>@<ver>` | `yarn upgrade <pkg>@<ver>` | `yarn up <pkg>@<ver>` | `pnpm update <pkg>` | `bun add <pkg>@<ver>` |
| Build | `npm run build` | `yarn build` | `yarn build` | `pnpm run build` | `bun run build` |
| Test | `npm test` | `yarn test` | `yarn test` | `pnpm test` | `bun test` |

## Non-JavaScript Projects

If the project is not JavaScript/Node.js, use the appropriate build/test commands:

- **Python**: `pip install -r requirements.txt`, `pytest`
- **Go**: `go build ./...`, `go test ./...`
- **Java/Maven**: `mvn compile`, `mvn test`
- **Java/Gradle**: `./gradlew build`, `./gradlew test`
