# N10.3 horizon contrast

#337 failed at EGO's bounded final velocity/acceleration feasibility check while localization and takeoff gates passed. #338 freezes one diagnostic contrast: keep the 16 m goal and all inputs fixed, reduce only planning horizon from 5 m to 2 m. Full success still requires independent 3D/yaw arrival, the 600 sim-second active hold, candidate limits, no prohibited contact and landed/disarmed readback.
