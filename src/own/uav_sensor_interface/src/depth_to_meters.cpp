#include <cmath>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/image_encodings.hpp"
#include "sensor_msgs/msg/image.hpp"

class DepthToMeters final : public rclcpp::Node
{
public:
  DepthToMeters()
  : Node("d435i_depth_to_meters")
  {
    const auto input_topic = declare_parameter<std::string>(
      "input_topic", "/sensors/d435i/depth/image_rect_raw");
    const auto output_topic = declare_parameter<std::string>(
      "output_topic", "/sensors/d435i/depth");
    meters_per_unit_ = declare_parameter<double>("meters_per_unit", 0.001);
    max_output_rate_hz_ = declare_parameter<double>("max_output_rate_hz", 0.0);
    if (!std::isfinite(max_output_rate_hz_) || max_output_rate_hz_ < 0.0) {
      throw std::invalid_argument("max_output_rate_hz must be finite and non-negative");
    }
    if (!std::isfinite(meters_per_unit_) || meters_per_unit_ <= 0.0) {
      throw std::invalid_argument("meters_per_unit must be finite and positive");
    }

    publisher_ = create_publisher<sensor_msgs::msg::Image>(
      output_topic, rclcpp::SensorDataQoS());
    subscription_ = create_subscription<sensor_msgs::msg::Image>(
      input_topic, rclcpp::SensorDataQoS(),
      std::bind(&DepthToMeters::on_depth, this, std::placeholders::_1));
    RCLCPP_INFO(
      get_logger(), "Converting %s to %s at %.9g m per 16UC1 unit; output cap %.3g Hz (0=unlimited)",
      input_topic.c_str(), output_topic.c_str(), meters_per_unit_, max_output_rate_hz_);
  }

private:
  void on_depth(const sensor_msgs::msg::Image::ConstSharedPtr input)
  {
    if (input->encoding != sensor_msgs::image_encodings::TYPE_16UC1) {
      warn_once("expected 16UC1 depth image");
      return;
    }
    const std::size_t row_bytes = static_cast<std::size_t>(input->width) * 2U;
    const std::size_t required_bytes = static_cast<std::size_t>(input->step) * input->height;
    if (input->width == 0U || input->height == 0U || input->step < row_bytes ||
      input->data.size() < required_bytes)
    {
      warn_once("invalid 16UC1 depth image dimensions or data length");
      return;
    }

    const auto now = std::chrono::steady_clock::now();
    if (logged_first_ && max_output_rate_hz_ > 0.0 &&
      std::chrono::duration<double>(now - last_output_).count() < 1.0 / max_output_rate_hz_)
    {
      return;
    }
    auto output = std::make_unique<sensor_msgs::msg::Image>();
    output->header = input->header;
    output->height = input->height;
    output->width = input->width;
    output->encoding = sensor_msgs::image_encodings::TYPE_32FC1;
    output->is_bigendian = 0U;
    output->step = input->width * 4U;
    output->data.resize(static_cast<std::size_t>(output->step) * output->height);

    for (std::size_t y = 0; y < input->height; ++y) {
      const auto * source_row = input->data.data() + y * input->step;
      auto * output_row = output->data.data() + y * output->step;
      for (std::size_t x = 0; x < input->width; ++x) {
        const auto * source_pixel = source_row + x * 2U;
        const std::uint16_t depth_units = input->is_bigendian
          ? static_cast<std::uint16_t>(
          (static_cast<std::uint16_t>(source_pixel[0]) << 8U) | source_pixel[1])
          : static_cast<std::uint16_t>(
          source_pixel[0] | (static_cast<std::uint16_t>(source_pixel[1]) << 8U));
        const float depth_m = depth_units == 0U
          ? 0.0F
          : static_cast<float>(depth_units) * static_cast<float>(meters_per_unit_);
        std::uint32_t bits = 0U;
        std::memcpy(&bits, &depth_m, sizeof(bits));
        const std::size_t offset = x * 4U;
        output_row[offset] = static_cast<std::uint8_t>(bits & 0xffU);
        output_row[offset + 1U] = static_cast<std::uint8_t>((bits >> 8U) & 0xffU);
        output_row[offset + 2U] = static_cast<std::uint8_t>((bits >> 16U) & 0xffU);
        output_row[offset + 3U] = static_cast<std::uint8_t>((bits >> 24U) & 0xffU);
      }
    }

    last_output_ = now;
    publisher_->publish(std::move(output));
    if (!logged_first_) {
      RCLCPP_INFO(
        get_logger(), "First depth converted: %ux%u 32FC1, frame=%s, source stamp preserved",
        input->width, input->height, input->header.frame_id.c_str());
      logged_first_ = true;
    }
  }

  void warn_once(const char * message)
  {
    if (!logged_warning_) {
      RCLCPP_ERROR(get_logger(), "Depth conversion stopped for invalid input: %s", message);
      logged_warning_ = true;
    }
  }

  double meters_per_unit_{0.001};
  double max_output_rate_hz_{0.0};
  std::chrono::steady_clock::time_point last_output_{};
  bool logged_first_{false};
  bool logged_warning_{false};
  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr publisher_;
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  try {
    rclcpp::spin(std::make_shared<DepthToMeters>());
  } catch (const std::exception & exception) {
    RCLCPP_FATAL(rclcpp::get_logger("d435i_depth_to_meters"), "%s", exception.what());
    rclcpp::shutdown();
    return 1;
  }
  rclcpp::shutdown();
  return 0;
}
