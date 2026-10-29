# N10.3 long-range calibration attempt

Protocol #336 ran as #337. Preflight and official takeoff admission passed. EGO accepted the 16 m goal, but path optimization could not produce a final dynamics-feasible spline after three bounded refinements; it aborted before READY trajectory publication. PX4/bridge landed and disarmed; contact evaluation passed. No horizontal goal leg or 600 sim-second hold was completed.

The logged cause is dynamics feasibility, but it does not isolate whether the 5 m local planning horizon or nonzero local target velocity caused the rejection. #338 will change only planning horizon (5 m to 2 m) while holding the target and speed/acceleration config fixed.
