# spdlog workspace metadata patch

- Upstream: `https://github.com/gabime/spdlog`
- Base commit: `eb3220622e73a4889eee355ffa37972b3cac3df5` (`v1.9.2`)
- License: MIT; patch adds only `colcon.pkg` and does not modify upstream source.
- Order: apply `0001-colcon-build-integration.patch` after checking out the base commit.
- Purpose: build the exact logger version required by Agent v2.4.3 in the workspace with bundled fmt, avoiding incompatibility with the system spdlog 1.12/fmt 9.
- Rebuild check: apply to a `git archive` of the base commit; the patched source manifest matches the imported checkout. See [Agent evidence](../../../progress/evidence/p0-agent-build.json).
