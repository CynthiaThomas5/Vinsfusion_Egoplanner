# N10.3 #377 result

## Task

Attempt one PX4 caller-cancel braking measurement at a speed chosen from the #376 observed near-peak range. User authorized continuing N10 and removal of project-added health gates after source audit.

## Frozen conditions

Single D435i Gazebo/PX4 SITL; runtime source/install SHA `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`; horizon 5 m, EGO max velocity 0.8 m/s/axis, max acceleration 0.25 m/s²/axis, `official_ego`; spawn `[-8,0,0.3,0,0,0]`; one +16 m / +0.10 m / +0.20 rad goal; read-only contacts. Trigger window `[0.70,0.80] m/s`.

## Result and decision

Two initial run-local ROS setup attempts exited before preflight or goal due unset shell variables. Independent six-second PX4/bridge readback confirmed landed/disarmed/no control. The run-local wrapper was corrected only to disable `nounset` during ROS/colcon setup sourcing, then the original freeze was extended with a pre-goal addendum and new driver hash.

Frozen identity matched. The goal finished before PX4 horizontal speed entered the window. PX4 horizontal peak was about 0.6479 m/s; EGO reference peak was about 0.7152 m/s. No cancel acknowledgement, replacement trajectory, or stop-band measurement was obtained. Contact evaluation found zero prohibited contacts; independent final readback confirmed LANDED, disarmed, control disabled, zero control. The project container was safely stopped.

As-of matching of PX4 local-position samples to the latest same-goal/epoch READY command found 110 valid candidates in `[0.60,0.66] m/s`, with the first at about 0.6013 m/s. New #378 will change only the measurement trigger window to `[0.60,0.66] m/s`; this does not impose a flight speed cap or acceptance threshold.

## User constraints carried forward

Project-added localization quality/freshness/depth/whole-curve gates remain removed per the prior audit. Keep epoch/frame/map identity, PX4-native preflight and EV fusion, the single PX4 bridge, official EGO collision/watchdog behavior, and read-only truth/contact observers. Preserve #377 as a failed measurement, not a pass.

## Open work

N10.3 still needs a valid caller-cancel stop sample, sufficient independent calibration/rationale, then N10.4–N10.7. N10 remains `in_progress`.
