# N10.3 #379 braking repeat protocol

## User constraints

Continue the authorized N10 goal. Keep the measurement speed evidence-based; the selected interval is a sample trigger, not a flight speed cap or acceptance threshold. Retain already-audited PX4-native and upstream behavior and do not restore removed project-local health gates.

## Basis

#378 is the first valid brake sample on runtime b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7. It triggered at PX4 horizontal 0.600867 m/s, entered the PX4 stop band after 4.844 simulated seconds, covered 1.376716 m horizontal truth path, and had zero prohibited contacts with safe landed/disarmed/control-disabled/zero-control terminal evidence.

## Frozen repeat

#379 starts a fresh Gazebo/PX4/VINS session with the same source/install SHA, horizon5/0.8/0.25 official_ego planner, spawn [-8,0,0.3], +16m/+0.10m/+0.20rad goal, [0.60,0.66] m/s actual PX4 trigger window, stop band and observers. This is repeat 2 of 3. No parameter, threshold or protocol changes.

## Status

Protocol and prelaunch identities are frozen. The new container has not started and no goal has been sent. N10.3 still needs repeatability and evidence synthesis for localization/map error, clearance, replanning, fault exits and supported scope.
