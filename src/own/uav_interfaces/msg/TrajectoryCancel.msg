# Cancellation is keyed to the active goal and VINS session. Consumers must
# ignore stale messages from another goal or epoch.
uint8 MODE_ABORT=0
uint8 MODE_STOP_HOLD=1
string goal_id
string epoch
uint8 mode
string reason
