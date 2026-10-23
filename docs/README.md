# Document map

[日本語](README.ja.md)

Every document has one role; other documents link to it instead of repeating its content. Every user-facing page comes as an English/Japanese pair (`name.md` / `name.ja.md`); only the agent instructions, the license/notice texts and 1.x's overlay manifest (a provenance record whose hashes have one owner) are English-only by design. Each line's changelog is a pair too: the English file is canonical and the GitHub Release is made from it. Update both when user-visible instructions change ([Contributing](../CONTRIBUTING.md)).

This map lists the repository's own pages, the pages every serving line shares and the 2.x and 3.x pages. The 1.x pages are listed by [1.x's document map](../v1/docs/README.md), with the owner of each 1.x fact.

## Repository

| Document | Role | EN | JA |
|---|---|---|---|
| Repository README | The serving lines, what BIZ means and does not mean, licensing at a glance, local data | [EN](../README.md) | [JA](../README.ja.md) |
| Contributing | CPU checks, publication audit, contribution rules | [EN](../CONTRIBUTING.md) | [JA](../CONTRIBUTING.ja.md) |
| Repository instructions | Rules for AI agents and operators editing this checkout | [EN](../AGENTS.md) | — |
| Licensing and notices | Apache-2.0 text, attribution, third-party provenance | [LICENSE](../LICENSE), [NOTICE](../NOTICE), [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md), [LICENSES/](../LICENSES/) | — |
| Licensing guide | Commercial use, modification and redistribution by artifact | [EN](licensing.md) | [JA](licensing.ja.md) |

## Hosts and fabric, for every line

| Document | Role | EN | JA |
|---|---|---|---|
| Host preparation | The kernel and driver to run, the multi-node RoCE failure and its workaround, the GPU clock cap | [EN](hosts.md) | [JA](hosts.ja.md) |
| Host tools | GPU clock cap unit, telemetry logger, cool-gate and thermal-watch | [EN](../host/README.md) | [JA](../host/README.ja.md) |
| QSFP network | Direct QSFP connection for the pair and the three-host ring, persistent NetworkManager profiles, per-host /32 addresses | [EN](qsfp-network.md) | [JA](qsfp-network.ja.md) |
| NCCL diagnostics | Two- and three-rank collective diagnostic, a moving GID index, channel count, limits | [EN](nccl-validation.md) | [JA](nccl-validation.ja.md) |

## Serving lines

| Line | Document map or pages | EN | JA |
|---|---|---|---|
| 1.x (vLLM) | Document map: README, setup runbook, changelog and every 1.x document, with the owner of each fact | [EN](../v1/docs/README.md) | [JA](../v1/docs/README.ja.md) |
| 2.x README | The 2.x line's overview: what it serves, how to start it, its defaults and measurements, its limits and what would change it | [EN](../v2/README.md) | [JA](../v2/README.ja.md) |
| 2.x setup runbook | Ordered steps from hosts to acceptance and stop | [EN](../v2/SETUP.md) | [JA](../v2/SETUP.ja.md) |
| 2.x validation | The reference values a 2.x launch is accepted against | [EN](../v2/docs/validation.md) | [JA](../v2/docs/validation.ja.md) |
| 2.x operations | Start outcomes, a rank that stops, a stop that leaves an engine, NCCL over sockets, a new container or image, a host that powered off, handing the hosts to 1.x | [EN](../v2/docs/operations.md) | [JA](../v2/docs/operations.ja.md) |
| 2.x decisions | What was tried for 2.x, adopted or rejected, with dates, measured effects and what would reopen each; 1.x measures not yet evaluated on 2.x | [EN](../v2/docs/decisions.md) | [JA](../v2/docs/decisions.ja.md) |
| 2.x benchmark method | How the release figures and the reference values were taken: hosts, cooling, prompts, engine commits | [EN](../v2/docs/benchmarks.md) | [JA](../v2/docs/benchmarks.ja.md) |
| 2.x changelog | 2.x releases; the English file is canonical | [EN](../v2/CHANGELOG.md) | [JA](../v2/CHANGELOG.ja.md) |
| 3.x README | The 3.x line's overview: what it serves on TensorFold's native engine, how to start it, its defaults and measurements, its limits and what would change it | [EN](../v3/README.md) | [JA](../v3/README.ja.md) |
| 3.x setup runbook | Ordered steps from hosts to acceptance and stop | [EN](../v3/SETUP.md) | [JA](../v3/SETUP.ja.md) |
| 3.x validation | The reference values a 3.x launch is accepted against | [EN](../v3/docs/validation.md) | [JA](../v3/docs/validation.ja.md) |
| 3.x operations | Start outcomes, a rank that stops, a stop that leaves an engine, NCCL over sockets, a new container or image, another checkpoint, a host that powered off, handing the hosts to 2.x | [EN](../v3/docs/operations.md) | [JA](../v3/docs/operations.ja.md) |
| 3.x benchmark method | How the release figures and the reference values were taken: hosts, cores, cooling, prompts | [EN](../v3/docs/benchmarks.md) | [JA](../v3/docs/benchmarks.ja.md) |
| 3.x changelog | 3.x releases; the English file is canonical | [EN](../v3/CHANGELOG.md) | [JA](../v3/CHANGELOG.ja.md) |

## Conventions

- Each line owns its version (`pyproject.toml`) and its changelog. Pushing a `vX.Y.Z` tag publishes the GitHub Release: `.github/workflows/release.yml` reads `vN/` for a `vN.*` tag, takes that version's section (`python tools/release_notes.py X.Y.Z`) and refuses a tag that disagrees with `pyproject.toml`, has no section or whose section heading has no release date.
- `python tools/check_publication.py` audits the whole repository: links and anchors, private paths and sensitive text, each line's required files and lock, that each Japanese page has its English page's headings, table rows and code blocks, and that every `docs/*.md` here is a link target of this map (Japanese pages of the Japanese map).
- The GitHub repository description and topics restate the README summary with the short name and without any measured number or version, because `tools/check_publication.py` cannot see them; when the summary changes, edit them with `gh repo edit`.
- Private implementation plans live in `docs/plans/`, untracked and excluded from publication; `docs/plans/README.md` indexes them locally and each plan's own leading status line owns its state. Raw records stay in `records/<run-id>/` and site configuration in `state/`, both untracked.
