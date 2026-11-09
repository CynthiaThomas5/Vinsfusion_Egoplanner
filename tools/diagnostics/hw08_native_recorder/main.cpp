// Read-only native diagnostic; no publishers, services or control interfaces.
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <stdexcept>

int main(int argc, char **argv) {
  if (argc != 2) throw std::runtime_error("Usage: hw08_native_recorder OUTPUT.csv");
  std::ofstream out(argv[1]);
  if (!out) throw std::runtime_error("Cannot open output");
  out << std::setprecision(17);
  out << "kind,source_ns,system_ns,monotonic_ns,px,py,pz,qx,qy,qz,qw,vx,vy,vz,wx,wy,wz,ax,ay,az\n";
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("hw08_native_readonly");
  auto prefix = [&](const char *kind, const builtin_interfaces::msg::Time &stamp) {
    const auto system = std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::system_clock::now().time_since_epoch()).count();
    const auto mono = std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count();
    out << kind << ',' << (int64_t(stamp.sec)*1000000000+stamp.nanosec)
        << ',' << system << ',' << mono;
  };
  auto imu = node->create_subscription<sensor_msgs::msg::Imu>("/sensors/d435i/imu",
    rclcpp::SensorDataQoS(), [&](sensor_msgs::msg::Imu::ConstSharedPtr m) {
      prefix("imu",m->header.stamp);
      const auto &w=m->angular_velocity, &a=m->linear_acceleration;
      out << ",0,0,0,0,0,0,1,0,0,0," << w.x << ',' << w.y << ',' << w.z
          << ',' << a.x << ',' << a.y << ',' << a.z << '\n';
    });
  auto pose = node->create_subscription<nav_msgs::msg::Odometry>("/localization/optimized_imu_odom",
    rclcpp::SensorDataQoS(), [&](nav_msgs::msg::Odometry::ConstSharedPtr m) {
      prefix("optimized",m->header.stamp);
      const auto &p=m->pose.pose.position; const auto &q=m->pose.pose.orientation;
      const auto &v=m->twist.twist.linear, &w=m->twist.twist.angular;
      out << ',' << p.x << ',' << p.y << ',' << p.z << ',' << q.x << ',' << q.y
          << ',' << q.z << ',' << q.w << ',' << v.x << ',' << v.y << ',' << v.z
          << ',' << w.x << ',' << w.y << ',' << w.z << ",0,0,0\n";
    });
  auto flush = node->create_wall_timer(std::chrono::seconds(1), [&] { out.flush(); });
  rclcpp::spin(node);
  out.flush(); rclcpp::shutdown();
}
