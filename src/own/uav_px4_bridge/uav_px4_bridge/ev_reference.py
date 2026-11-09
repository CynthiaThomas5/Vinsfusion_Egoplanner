"""Bind an EV world to an independently aligned PX4 local NED reference once per epoch."""
from dataclasses import replace
import math
from .trajectory import angle_difference,apply_ned_yaw_offset,rotate_ned_yaw


def yaw(q):
    if len(q)!=4 or not all(math.isfinite(x) for x in q) or abs(sum(x*x for x in q)-1.)>.02:
        raise ValueError('invalid_reference_quaternion')
    w,x,y,z=q
    return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))


class EVNEDReference:
    def __init__(self):
        self.samples={};self.alignment=None;self.epoch=None

    def update(self,kind,message,receipt_ns):
        if self.alignment is None:self.samples[kind]=(message,receipt_ns)

    def apply(self,values,system_ns,monotonic_ns):
        if self.epoch is not None and values.epoch!=self.epoch:
            raise ValueError('ev_reference_epoch_changed')
        if self.alignment is None:
            for kind,budget in (('attitude',.5),('local',.5),('flags',2.)):
                if kind not in self.samples:raise ValueError('waiting_for_independent_px4_heading')
                message,receipt=self.samples[kind]
                age=(system_ns-int(message.timestamp)*1000)/1e9
                if (not -.02<=age<=budget or not 0<=(monotonic_ns-receipt)/1e9<=budget):
                    raise ValueError('px4_heading_reference_stale_or_future')
            attitude=self.samples['attitude'][0];local=self.samples['local'][0];flags=self.samples['flags'][0]
            if (not flags.cs_yaw_align or not local.heading_good_for_control or flags.cs_ev_yaw
                    or flags.cs_mag_fault or flags.cs_mag_field_disturbed):
                raise ValueError('waiting_for_independent_px4_heading')
            if max(abs(values.timestamp_sample-int(m.timestamp))/1e6 for m in (attitude,local))>.12:
                raise ValueError('px4_heading_reference_unpaired')
            target_yaw=yaw(tuple(attitude.q));offset=angle_difference(target_yaw,yaw(values.quaternion_ned_frd_wxyz))
            # Unknown position is an explicitly free local origin; valid components
            # keep PX4's existing origin, avoiding a needless position jump.
            target=(local.x if local.xy_valid else 0.,local.y if local.xy_valid else 0.,local.z if local.z_valid else 0.)
            if not all(math.isfinite(v) for v in target):raise ValueError('invalid_reference_position')
            rotated=rotate_ned_yaw(values.position_ned,offset)
            self.alignment={'source':'px4_pre_ev_aligned_yaw','epoch':values.epoch,
                'yaw_offset_ned':offset,'origin_offset_ned':tuple(t-p for t,p in zip(target,rotated)),
                'reference_attitude_stamp_us':int(attitude.timestamp),
                'reference_flags_stamp_us':int(flags.timestamp),'target_yaw_ned':target_yaw,
                'position_components_valid':(bool(local.xy_valid),bool(local.xy_valid),bool(local.z_valid))}
            self.epoch=values.epoch
        a=self.alignment;rotated=rotate_ned_yaw(values.position_ned,a['yaw_offset_ned'])
        return replace(values,position_ned=tuple(x+y for x,y in zip(rotated,a['origin_offset_ned'])),
            quaternion_ned_frd_wxyz=apply_ned_yaw_offset(values.quaternion_ned_frd_wxyz,a['yaw_offset_ned']))
