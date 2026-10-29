"""Structural validation for one depth stream; age is reported, not gated."""
import math


class DepthFreshnessGate:
    STATES = {'WAITING': 0, 'READY': 1, 'STALE': 2, 'INVALID': 3, 'LOCKED': 4}

    def __init__(self, policy, started_wall):
        for key in ['startup_timeout_wall_s', 'status_period_wall_s']:
            if not math.isfinite(policy[key]) or policy[key] <= 0:
                raise ValueError('Invalid depth gate limit: ' + key)
        for key in ['width', 'height']:
            if type(policy[key]) is not int or policy[key] <= 0:
                raise ValueError('Invalid depth image dimension: ' + key)
        for key in ['expected_frame', 'expected_encoding']:
            if not isinstance(policy[key], str) or not policy[key]:
                raise ValueError('Invalid depth image contract: ' + key)
        self.policy = policy
        self.started_wall = started_wall
        self.last_receipt_wall = None
        self.last_stamp_ns = None
        self.received_count = 0
        self.state = 'WAITING'
        self.reason = 'waiting_for_depth'

    @staticmethod
    def stamp_ns(msg):
        return msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec

    def observe(self, msg, wall):
        self.received_count += 1
        if self.state == 'LOCKED':
            return False
        if msg.header.frame_id != self.policy['expected_frame']:
            self.state, self.reason = 'INVALID', 'depth_frame_mismatch'
            return False
        if msg.encoding != self.policy['expected_encoding']:
            self.state, self.reason = 'INVALID', 'depth_encoding_mismatch'
            return False
        if (msg.width != self.policy['width'] or msg.height != self.policy['height']
                or msg.step < msg.width * 4 or len(msg.data) < msg.step * msg.height):
            self.state, self.reason = 'INVALID', 'depth_layout_invalid'
            return False
        stamp = self.stamp_ns(msg)
        if stamp < 0 or (self.last_stamp_ns is not None and stamp <= self.last_stamp_ns):
            self.state, self.reason = 'LOCKED', 'depth_stamp_not_increasing'
            return False
        self.last_stamp_ns = stamp
        self.last_receipt_wall = wall
        self.state, self.reason = 'READY', 'structurally_valid_depth'
        return True

    def tick(self, wall):
        if self.state == 'LOCKED':
            return self.state
        if self.last_receipt_wall is None:
            if wall - self.started_wall >= self.policy['startup_timeout_wall_s']:
                self.state, self.reason = 'STALE', 'depth_missing'
            return self.state
        return self.state
