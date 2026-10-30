---
status: accepted
date: 2026-10-30
decision-makers: ["Na'aman Hirschfeld"]
amends: ["0033"]
---

# Shared xberg brand assets for the docs site

## Context and Problem Statement

[ADR 0024](0024-documentation-site-and-web-presence.md) kept the amber/pixel identity in
`docs/assets/` (banner, favicon, logo and social-preview files).
[ADR 0033](0033-org-migration-docs-domain-and-shared-theme.md) superseded it and moved the site to
the shared `@xberg-io/docs-theme`, removing the vendored brand files under the site directory, but
it did not name `docs/assets/`. Those six files stayed in the repository after nothing referenced
them, and they still showed the retired identity.

## Decision Drivers

* One brand source for the organization: xberg-io/assets, served from jsDelivr.
* No unreferenced brand copies that drift from it.

## Considered Options

* Delete `docs/assets/` and record that the shared assets are the only brand source.
* Keep `docs/assets/` as an archive of the old identity.

## Decision Outcome

Chosen option: "Delete `docs/assets/` and record that the shared assets are the only brand source",
because the docs site already takes its brand from the shared theme, which loads xberg-io/assets
from jsDelivr, and an unreferenced copy only drifts.

* The docs site uses `@xberg-io/docs-theme` through `xbergStarlightConfig()`, which loads the xberg
  brand assets from xberg-io/assets on jsDelivr (theme 0.4.1 pins `@v1.0.0`).
* The only local brand files are `docs-site/src/assets/hero-logo.svg` and `hero-logo-light.svg`,
  byte-identical to `assets@v1` `docs/hero-logo.svg` and `docs/hero-logo-light.svg`, the hero
  exception of
  [org ADR-0014](https://github.com/xberg-io/agent-conventions/blob/main/adrs/0014-shared-assets-and-distribution-channels.md).
* The amber/pixel identity in `docs/assets/` (`banner.svg`, `favicon.svg`, `logo.svg`, `logo.png`,
  `logo@2x.png`, `social-preview.png`) is retired and deleted.

### Consequences

* Good, because a brand change reaches the site through the theme and the assets repository alone.
* Bad, because the old identity survives only in git history.

### Confirmation

`docs-site/astro.config.mjs` builds the Starlight config with `xbergStarlightConfig()` from
`@xberg-io/docs-theme`, a dependency in `docs-site/package.json`.
`docs-site/src/content/docs/index.mdx` imports the hero pair from `docs-site/src/assets/`, whose git
blobs equal `assets@v1:docs/hero-logo.svg` and `assets@v1:docs/hero-logo-light.svg`. `docs/assets/`
no longer exists; `git grep docs/assets` matches only ADR 0024 and this record.
