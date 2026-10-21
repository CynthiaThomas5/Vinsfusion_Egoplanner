# Micro XRCE-DDS Agent workspace integration patch

- Upstream: `https://github.com/eProsima/Micro-XRCE-DDS-Agent`
- Base commit: `73622810d984349b80bbac0ef55fc0b694d62222` (`v2.4.3`)
- License: Apache-2.0; this patch changes only the project's colcon metadata.
- Order: apply `0001-colcon-build-integration.patch` after checking out the base commit.
- Purpose: build Agent in the workspace against pinned `spdlog`, system Fast-DDS/Fast-CDR from the pinned Jazzy base, and avoid CMake superbuild downloads. Disable Agent P2P/discovery/socketcan/security and tests; retain UDP4 support.
- Rebuild check: apply to a `git archive` of the base commit; the 213-file patched source manifest matches the imported checkout. See [Agent evidence](../../../progress/evidence/p0-agent-build.json).
- Validation status: the standalone CMake build and CLI help smoke check passed. Full colcon integration is validated separately in the clean workspace build evidence after the metadata patch.
