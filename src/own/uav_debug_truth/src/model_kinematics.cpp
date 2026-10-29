// SPDX-License-Identifier: Apache-2.0
// Read-only physics-state publisher. It never applies forces or control commands.
#include <chrono>
#include <cmath>
#include <memory>
#include <string>
#include <gz/common/Console.hh>
#include <gz/msgs/odometry.pb.h>
#include <gz/msgs/Utility.hh>
#include <gz/plugin/Register.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/transport/Node.hh>

namespace uav::debug_truth
{
class ModelKinematics final : public gz::sim::System,
    public gz::sim::ISystemConfigure, public gz::sim::ISystemPostUpdate
{
 public:
  void Configure(const gz::sim::Entity &entity,
      const std::shared_ptr<const sdf::Element> &sdf,
      gz::sim::EntityComponentManager &ecm, gz::sim::EventManager &) override
  {
    model = gz::sim::Model(entity);
    if (!model.Valid(ecm))
    {
      gzerr << "ModelKinematics requires a model entity\n";
      return;
    }
    link = gz::sim::Link(model.CanonicalLink(ecm));
    if (!link.Valid(ecm))
    {
      gzerr << "ModelKinematics canonical link unavailable\n";
      return;
    }
    // Request observable components only; no velocity/force command is set.
    link.EnableVelocityChecks(ecm);
    topic = sdf->Get<std::string>("topic", "/debug_truth/model_kinematics").first;
    publisher = node.Advertise<gz::msgs::Odometry>(topic);
    enabled = true;
  }

  void PostUpdate(const gz::sim::UpdateInfo &info,
      const gz::sim::EntityComponentManager &ecm) override
  {
    if (!enabled || info.paused || info.dt <= std::chrono::steady_clock::duration::zero())
      return;
    const auto modelPose = gz::sim::worldPose(model.Entity(), ecm);
    const auto linkPose = gz::sim::worldPose(link.Entity(), ecm);
    // SDK offset is expressed from the canonical link origin in its own frame.
    const auto offset = linkPose.Rot().RotateVectorReverse(modelPose.Pos() - linkPose.Pos());
    const auto velocity = link.WorldLinearVelocity(ecm, offset);
    const auto angular = link.WorldAngularVelocity(ecm);
    if (!velocity || !angular)
      return;
    for (const auto value : {velocity->X(), velocity->Y(), velocity->Z(),
                            angular->X(), angular->Y(), angular->Z()})
      if (!std::isfinite(value))
        return;
    const auto stamp = std::chrono::duration_cast<std::chrono::nanoseconds>(info.simTime).count();
    gz::msgs::Odometry message;
    auto *header = message.mutable_header();
    header->mutable_stamp()->set_sec(stamp / 1000000000);
    header->mutable_stamp()->set_nsec(stamp % 1000000000);
    const auto field = [header](const std::string &key, const std::string &value)
    {
      auto *data = header->add_data();
      data->set_key(key);
      data->add_value(value);
    };
    field("schema", "uav-model-kinematics/v1");
    field("frame_id", "world");
    field("child_frame_id", model.Name(ecm));
    field("pose_reference", "model_origin");
    field("linear_velocity_reference", "model_origin");
    field("linear_velocity_frame", "world");
    field("angular_velocity_frame", "world");
    field("velocity_kind", "instantaneous_physics_components");
    field("source", "canonical_link_world_components_with_sdk_point_transform");
    gz::msgs::Set(message.mutable_pose(), modelPose);
    gz::msgs::Set(message.mutable_twist()->mutable_linear(), *velocity);
    gz::msgs::Set(message.mutable_twist()->mutable_angular(), *angular);
    publisher.Publish(message);
  }

 private:
  gz::sim::Model model;
  gz::sim::Link link;
  gz::transport::Node node;
  gz::transport::Node::Publisher publisher;
  std::string topic;
  bool enabled{false};
};
}
GZ_ADD_PLUGIN(uav::debug_truth::ModelKinematics, gz::sim::System,
    gz::sim::ISystemConfigure, gz::sim::ISystemPostUpdate)
