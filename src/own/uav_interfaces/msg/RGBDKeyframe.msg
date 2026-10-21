# One synchronized, epoch-bound RGB-D sample. Image/CameraInfo source headers
# are preserved; each pose is evaluated at its corresponding image stamp.
std_msgs/Header header
string epoch
string map_id
sensor_msgs/Image color
sensor_msgs/Image depth
sensor_msgs/CameraInfo color_camera_info
sensor_msgs/CameraInfo depth_camera_info
geometry_msgs/PoseStamped color_pose
geometry_msgs/PoseStamped depth_pose
string calibration_sha256
