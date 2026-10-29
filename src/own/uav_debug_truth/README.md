# Read-only Gazebo physics kinematics

`libuav_truth_kinematics.so` reads the canonical link's physics components after each positive solver update. Gazebo's native point-velocity API transforms the canonical-link state to the parent model origin. Pose, instantaneous linear velocity and angular velocity are published in world coordinates on `/debug_truth/model_kinematics` with explicit reference metadata.

This plugin never sends force, velocity, PX4 or navigation commands. `EnableVelocityChecks` requests observable components only. Its messages are evaluation inputs, never navigation feedback. It is enabled only by the optional run-local observer overlay (`D435I_N10_KINEMATICS=1`, with the existing contact overlay). The main camera/vehicle geometry remains unchanged.

The SDK is supplied by the fixed Gazebo 8 image. The package environment hook exposes the plugin to Gazebo. `record_truth.py` can record a separate identity-bound kinematics ledger. Missing/invalid observations produce insufficient offline evidence and do not add launch, cancellation or landing decisions.
