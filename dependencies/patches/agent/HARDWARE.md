# ARM serial framing recovery patch

`0002-serial-framing-resync.patch` is a hardware profile patch against eProsima Micro-XRCE-DDS-Agent v2.4.3, commit `73622810d984349b80bbac0ef55fc0b694d62222` (Apache-2.0). It changes only `src/cpp/transport/stream_framing/StreamFramingProtocol.cpp`; baseline SHA256 `a22d5164bf6af6f69b749e2442466af22e7fbf5ad0cb55ac1168fa1197f866f4`.

The observed source is `/home/jetson/Micro-XRCE-DDS-Agent`, with a clean Git status. Source and `/usr/local` are read-only inputs to the build. The patch recognizes a newly consumed frame delimiter before refilling the receive buffer in header/CRC states, so a malformed preceding frame cannot consume the following valid frame. CRC checks remain mandatory; no damaged frame is repaired or accepted.

Order for this hardware build: upstream v2.4.3 → `0002`. The existing `0001-colcon-build-integration.patch` changes package metadata only and may precede it for a colcon checkout. This patch is not added to the simulation default patch list and does not change its frozen Agent.

On the measured Nano, build with:

```bash
python3 tools/build_hardware_agent_framing.py \
  --source /home/jetson/Micro-XRCE-DDS-Agent \
  --output artifacts/runs/RUN/agent-framing-build
```

The builder requires the existing build objects and exact installed baseline `cb802f0a2f3e2bdf5af83d9fa64fb56e84bbcbbd515020d5e40eef7052585651`. It first reproduces that library byte for byte, then rebuilds only the patched translation unit and links a separate candidate. It records input hashes and runs `tools/test_agent_framing.cpp` on ARM. A different baseline must be audited rather than bypassing the identity check. No installation or service mutation occurs in the builder.

Real UART capture, original/candidate replay, runtime library mapping, verification scope and remaining timing limits are in `progress/evidence/dds-latency-20261105-006.md`. This fixes a measured parser defect; it does not qualify all serial timing, external-vision fusion, control or flight.
