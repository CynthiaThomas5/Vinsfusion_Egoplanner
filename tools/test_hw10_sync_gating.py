#!/usr/bin/env python3
"""Replay recorded RTTs through production EV/control methods, without ROS nodes.

Only the RTT and receipt intervals are recorded; all healthy localization,
mount/reference and control demand are synthetic. Publishers are memory lists.
This diagnoses gating, not physical control or estimator fusion.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nav_msgs.msg import Odometry
from px4_msgs.msg import TimesyncStatus, VehicleAttitude, VehicleLocalPosition, EstimatorStatusFlags
from uav_interfaces.msg import LocalizationStatus
from uav_px4_bridge.hardware_ev import HardwareEVPath
from uav_px4_bridge.px4_bridge_node import Px4BridgeNode
from uav_px4_bridge.time_mapping import SystemClockMapper
from uav_px4_bridge.control_state import OffboardSupervisor, READINESS_REQUIREMENTS

ROOT = Path(__file__).resolve().parents[1]


class MemoryNode:
    def get_parameter(self, key):
        return SimpleNamespace(value=True if key == 'allow_approximate_bench_ev' else
                               False if key == 'use_sim_time' else '')

    def create_publisher(self, *args):
        return SimpleNamespace(publish=lambda msg: None)

    def create_subscription(self, *args, **kwargs):
        return None

    def create_timer(self, *args, **kwargs):
        return None

    def get_logger(self):
        return SimpleNamespace(warning=lambda *args: None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recording', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((ROOT/'config/hardware/px4_bridge_ev.json').read_text())
    profile = json.loads((ROOT/'config/hardware/px4_profile.json').read_text())
    frames = json.loads((ROOT/'config/components/px4_bridge/frames_vio_closed_loop.json').read_text())
    assert config['timesync_max_rtt_us'] == 10000 and config['timesync_max_age_s'] == 2
    base = 1700000000000000000
    clock = [base, 10000000000]
    counts = dict(ev=0, mode=0, setpoint=0)
    published = {k: [] for k in counts}

    def publisher(key):
        return SimpleNamespace(publish=lambda msg: published[key].append(clock[1]/1e9))

    with patch('time.time_ns', side_effect=lambda: clock[0]), patch('time.monotonic_ns', side_effect=lambda: clock[1]):
        ev = HardwareEVPath(MemoryNode(), config, profile, frames,
                            str(ROOT/'config/hardware/rig.json'), 'ev_only')
        ev.ev_pub = publisher('ev')
        control = SimpleNamespace(hardware_runtime=True, config=config,
            clock_mapper=SystemClockMapper(.868306, .02, .05, False),
            mode_pub=publisher('mode'), setpoint_pub=publisher('setpoint'),
            timesync=None, timesync_receipt_ns=None, trajectory_fault='', _position_for_output=lambda *a: ((0., 0., 0.), 0.))
        control._px4_now_us = lambda now: Px4BridgeNode._px4_now_us(control, now)
        epoch = 'a'*32

        def update_sync(rtt):
            sync = TimesyncStatus(timestamp=clock[0]//1000, source_protocol=2,
                round_trip_time=int(rtt), estimated_offset=100000000-clock[0]//1000)
            ev.on_timesync(sync)
            control._now_ns = lambda: clock[1]
            Px4BridgeNode._on_timesync(control, sync)

        def tick():
            now = clock[0]//1000
            ev.ned_reference.update('attitude', VehicleAttitude(timestamp=now, q=[1., 0., 0., 0.]), clock[1])
            ev.ned_reference.update('local', VehicleLocalPosition(timestamp=now, heading_good_for_control=True), clock[1])
            ev.ned_reference.update('flags', EstimatorStatusFlags(timestamp=now, cs_yaw_align=True), clock[1])
            ev.on_health(LocalizationStatus(epoch=epoch, valid=True, state=LocalizationStatus.TRACKING))
            msg = Odometry()
            msg.header.frame_id = 'odom_'+epoch
            msg.child_frame_id = frames['source_body_frame_prefix']+epoch
            msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(clock[0]-10000000, 1000000000)
            msg.pose.pose.orientation.w = 1.
            ev.on_odometry(msg)
            Px4BridgeNode._publish_control(control, SimpleNamespace(publish_offboard=True, command=None), {}, clock[1])

        # Boundary, recovery, and stale accepted sample remain fail closed.
        for rtt, expected in [(10000, True), (10001, True), (1000, True)]:
            clock[0] += 40000000; clock[1] += 40000000
            update_sync(rtt); before = {k: len(v) for k, v in published.items()}; tick()
            assert all((len(published[k]) > before[k]) == expected for k in before), (rtt, ev.reason)
        clock[0] += 2100000000; clock[1] += 2100000000
        before = {k: len(v) for k, v in published.items()}; tick()
        assert all(len(published[k]) == before[k] for k in before)
        assert ev.reason == control.px4_timestamp_error == 'px4_timesync_stale'

        details = []
        ev.detail_pub = SimpleNamespace(publish=lambda msg: details.append(json.loads(msg.data)))
        ev.health.valid = False
        ev.tick()
        assert details[-1]['reason'] == 'localization_invalid_or_stale'
        ev.on_health(LocalizationStatus(epoch=epoch, valid=True, state=LocalizationStatus.TRACKING))
        ev.last_receipt = clock[1]-300000000
        ev.tick()
        assert details[-1]['reason'] == 'odometry_receipt_stale'
        ev.timesync = ev.sync_receipt = None
        control.timesync = control.timesync_receipt_ns = None
        update_sync(10001)
        assert ev.timesync is None and control.timesync is None

        replay = None
        if args.recording:
            syncs = [x for line in args.recording.open() if
                     (x := json.loads(line))['topic'] == '/fmu/out/timesync_status']
            assert syncs
            # New mapper: the previous stale test must not affect replay timing.
            ev.mapper = SystemClockMapper(.868306, .02, .05, False)
            control.clock_mapper = SystemClockMapper(.868306, .02, .05, False)
            ev.last_stamp = ev.last_ev_attempt_mono = None
            ev.timesync = ev.sync_receipt = None
            control.timesync = control.timesync_receipt_ns = None
            for values in published.values(): values.clear()
            start = syncs[0]['monotonic_s']; duration = syncs[-1]['monotonic_s']-start
            index = 0; blocked = {}; total = 0
            for step in range(int(duration*25)+1):
                t = step*.04
                clock[:] = [base+int(t*1e9), 10000000000+int(t*1e9)]
                while index < len(syncs) and syncs[index]['monotonic_s']-start <= t:
                    sample = syncs[index]; receipt_t = sample['monotonic_s']-start
                    saved = list(clock)
                    clock[:] = [base+int(receipt_t*1e9), 10000000000+int(receipt_t*1e9)]
                    update_sync(sample['message']['round_trip_time']); clock[:] = saved
                    index += 1
                tick(); total += 1
                if ev.reason != 'ev_only': blocked[ev.reason] = blocked.get(ev.reason, 0)+1
            gaps = {k: max((b-a for a, b in zip(v, v[1:])), default=None) for k, v in published.items()}
            assert len(published['ev']) == len(published['mode']) == len(published['setpoint'])
            assert blocked.get('px4_timesync_rtt_high', 0) == 0
            replay = dict(samples=len(syncs), duration_s=duration, attempts=total,
                published={k:len(v) for k,v in published.items()}, blocked=blocked, max_gap_s=gaps,
                assumption='Recorded RTT/receipt spacing; normalized source time, otherwise healthy synthetic inputs; direct demanded output, no supervisor/flight')
    result = dict(scope='No rclpy.init, no ROS nodes, all publishers in memory',
        boundary_recovery_stale_checks='PASS', config_rtt_us=10000, config_age_s=2, replay=replay)
    snapshot = {key:True for key,_ in READINESS_REQUIREMENTS}
    snapshot.update(gnss_position_aiding=False, gnss_velocity_aiding=False,
        gnss_height_aiding=False, gnss_yaw_aiding=False, armed=False, landed=True,
        position_ned=(0.,0.,0.), heading_ned=0.)
    supervisor = OffboardSupervisor(profile, frames, 1., 1., .3, .2, 1., 1., 3)
    assert supervisor.enable(snapshot, 0.)[0]
    snapshot['px4_time_domain_valid'] = False
    supervisor.step(snapshot, .1)
    assert supervisor.phase == supervisor.DISABLED and supervisor.reason == 'px4_time_domain_invalid'
    result['unarmed_prestream_bad_sync'] = 'DISABLED / px4_time_domain_invalid'
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
