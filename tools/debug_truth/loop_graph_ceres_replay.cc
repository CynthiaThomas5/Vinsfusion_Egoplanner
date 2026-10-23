// Standalone replay of the pinned VINS loop_fusion 4DoF residual blocks.
// Input is a whitespace-delimited keyframe graph prepared by replay_loop_yaw_graph.py.
#include <ceres/ceres.h>
#include <Eigen/Dense>

#include <cmath>
#include <iomanip>
#include <iostream>
#include <vector>

template <typename T>
T NormalizeAngle(const T& angle_degrees) {
  if (angle_degrees > T(180.0)) return angle_degrees - T(360.0);
  if (angle_degrees < T(-180.0)) return angle_degrees + T(360.0);
  return angle_degrees;
}

struct AngleManifoldFunctor {
  template <typename T>
  bool Plus(const T* theta_radians, const T* delta_theta_radians,
            T* theta_radians_plus_delta) const {
    *theta_radians_plus_delta =
        NormalizeAngle(*theta_radians + *delta_theta_radians);
    return true;
  }

  template <typename T>
  bool Minus(const T* y, const T* x, T* y_minus_x) const {
    *y_minus_x = NormalizeAngle(*y - *x);
    return true;
  }
};

template <typename T>
void YawPitchRollToRotationMatrix(const T yaw, const T pitch, const T roll,
                                  T R[9]) {
  const T y = yaw / T(180.0) * T(M_PI);
  const T p = pitch / T(180.0) * T(M_PI);
  const T r = roll / T(180.0) * T(M_PI);
  R[0] = cos(y) * cos(p);
  R[1] = -sin(y) * cos(r) + cos(y) * sin(p) * sin(r);
  R[2] = sin(y) * sin(r) + cos(y) * sin(p) * cos(r);
  R[3] = sin(y) * cos(p);
  R[4] = cos(y) * cos(r) + sin(y) * sin(p) * sin(r);
  R[5] = -cos(y) * sin(r) + sin(y) * sin(p) * cos(r);
  R[6] = -sin(p);
  R[7] = cos(p) * sin(r);
  R[8] = cos(p) * cos(r);
}

template <typename T>
void RotationMatrixTranspose(const T R[9], T inverse_R[9]) {
  inverse_R[0] = R[0]; inverse_R[1] = R[3]; inverse_R[2] = R[6];
  inverse_R[3] = R[1]; inverse_R[4] = R[4]; inverse_R[5] = R[7];
  inverse_R[6] = R[2]; inverse_R[7] = R[5]; inverse_R[8] = R[8];
}

template <typename T>
void RotationMatrixRotatePoint(const T R[9], const T point[3], T rotated[3]) {
  rotated[0] = R[0] * point[0] + R[1] * point[1] + R[2] * point[2];
  rotated[1] = R[3] * point[0] + R[4] * point[1] + R[5] * point[2];
  rotated[2] = R[6] * point[0] + R[7] * point[1] + R[8] * point[2];
}

struct FourDOFError {
  FourDOFError(double tx, double ty, double tz, double relative_yaw,
               double pitch_i, double roll_i)
      : tx(tx), ty(ty), tz(tz), relative_yaw(relative_yaw),
        pitch_i(pitch_i), roll_i(roll_i) {}

  template <typename T>
  bool operator()(const T* const yaw_i, const T* ti,
                  const T* const yaw_j, const T* tj,
                  T* residuals) const {
    const T delta_world[3] = {tj[0] - ti[0], tj[1] - ti[1], tj[2] - ti[2]};
    T world_R_i[9], inverse_R[9], relative_t[3];
    YawPitchRollToRotationMatrix(yaw_i[0], T(pitch_i), T(roll_i), world_R_i);
    RotationMatrixTranspose(world_R_i, inverse_R);
    RotationMatrixRotatePoint(inverse_R, delta_world, relative_t);
    residuals[0] = relative_t[0] - T(tx);
    residuals[1] = relative_t[1] - T(ty);
    residuals[2] = relative_t[2] - T(tz);
    residuals[3] = NormalizeAngle(yaw_j[0] - yaw_i[0] - T(relative_yaw));
    return true;
  }

  static ceres::CostFunction* Create(double tx, double ty, double tz,
                                     double relative_yaw, double pitch_i,
                                     double roll_i) {
    return new ceres::AutoDiffCostFunction<FourDOFError, 4, 1, 3, 1, 3>(
        new FourDOFError(tx, ty, tz, relative_yaw, pitch_i, roll_i));
  }

  double tx, ty, tz, relative_yaw, pitch_i, roll_i;
};

struct FourDOFLoopError {
  FourDOFLoopError(double tx, double ty, double tz, double relative_yaw,
                   double pitch_i, double roll_i, double yaw_scale)
      : tx(tx), ty(ty), tz(tz), relative_yaw(relative_yaw),
        pitch_i(pitch_i), roll_i(roll_i), yaw_scale(yaw_scale) {}

  template <typename T>
  bool operator()(const T* const yaw_i, const T* ti,
                  const T* const yaw_j, const T* tj,
                  T* residuals) const {
    const T delta_world[3] = {tj[0] - ti[0], tj[1] - ti[1], tj[2] - ti[2]};
    T world_R_i[9], inverse_R[9], relative_t[3];
    YawPitchRollToRotationMatrix(yaw_i[0], T(pitch_i), T(roll_i), world_R_i);
    RotationMatrixTranspose(world_R_i, inverse_R);
    RotationMatrixRotatePoint(inverse_R, delta_world, relative_t);
    residuals[0] = relative_t[0] - T(tx);
    residuals[1] = relative_t[1] - T(ty);
    residuals[2] = relative_t[2] - T(tz);
    residuals[3] = NormalizeAngle(yaw_j[0] - yaw_i[0] - T(relative_yaw))
                   * T(yaw_scale);
    return true;
  }

  static ceres::CostFunction* Create(double tx, double ty, double tz,
                                     double relative_yaw, double pitch_i,
                                     double roll_i, double yaw_scale) {
    return new ceres::AutoDiffCostFunction<FourDOFLoopError, 4, 1, 3, 1, 3>(
        new FourDOFLoopError(tx, ty, tz, relative_yaw, pitch_i, roll_i,
                             yaw_scale));
  }

  double tx, ty, tz, relative_yaw, pitch_i, roll_i, yaw_scale;
};

struct Node {
  int index = -1;
  int loop_index = -1;
  Eigen::Vector3d vio_t = Eigen::Vector3d::Zero();
  Eigen::Quaterniond vio_q = Eigen::Quaterniond::Identity();
  Eigen::Vector3d loop_t = Eigen::Vector3d::Zero();
  double loop_yaw = 0.0;
  double yaw = 0.0;
  double pitch = 0.0;
  double roll = 0.0;
  double t[3] = {0.0, 0.0, 0.0};
};

Eigen::Vector3d R2ypr(const Eigen::Matrix3d& R) {
  const Eigen::Vector3d n = R.col(0);
  const Eigen::Vector3d o = R.col(1);
  const Eigen::Vector3d a = R.col(2);
  const double y = std::atan2(n(1), n(0));
  const double p = std::atan2(-n(2), n(0) * std::cos(y) + n(1) * std::sin(y));
  const double r = std::atan2(a(0) * std::sin(y) - a(1) * std::cos(y),
                              -o(0) * std::sin(y) + o(1) * std::cos(y));
  return Eigen::Vector3d(y, p, r) / M_PI * 180.0;
}

int main() {
  int first_index = -1, current_index = -1, count = 0;
  double yaw_scale = 0.0;
  if (!(std::cin >> first_index >> current_index >> yaw_scale >> count) ||
      first_index < 0 || current_index < first_index ||
      count != current_index - first_index + 1 || yaw_scale <= 0.0) {
    std::cerr << "invalid replay header\n";
    return 2;
  }

  std::vector<Node> nodes(static_cast<std::size_t>(count));
  for (int offset = 0; offset < count; ++offset) {
    Node& n = nodes[static_cast<std::size_t>(offset)];
    double qx, qy, qz, qw;
    double ltx, lty, ltz;
    int has_loop = 0;
    if (!(std::cin >> n.index >> n.vio_t.x() >> n.vio_t.y() >> n.vio_t.z()
                  >> qx >> qy >> qz >> qw >> has_loop >> n.loop_index
                  >> ltx >> lty >> ltz >> n.loop_yaw)) {
      std::cerr << "invalid replay node row\n";
      return 2;
    }
    if (n.index != first_index + offset) {
      std::cerr << "noncontiguous keyframe indices\n";
      return 2;
    }
    n.vio_q = Eigen::Quaterniond(qw, qx, qy, qz).normalized();
    n.loop_t = Eigen::Vector3d(ltx, lty, ltz);
    const Eigen::Vector3d ypr = R2ypr(n.vio_q.toRotationMatrix());
    n.yaw = ypr.x(); n.pitch = ypr.y(); n.roll = ypr.z();
    n.t[0] = n.vio_t.x(); n.t[1] = n.vio_t.y(); n.t[2] = n.vio_t.z();
    if (!has_loop) n.loop_index = -1;
  }

  ceres::Problem problem;
  ceres::Manifold* angle_manifold =
      new ceres::AutoDiffManifold<AngleManifoldFunctor, 1, 1>();
  ceres::LossFunction* loop_loss = new ceres::HuberLoss(0.1);

  for (int i = 0; i < count; ++i) {
    Node& current = nodes[static_cast<std::size_t>(i)];
    problem.AddParameterBlock(&current.yaw, 1, angle_manifold);
    problem.AddParameterBlock(current.t, 3);
    if (current.index == first_index) {
      problem.SetParameterBlockConstant(&current.yaw);
      problem.SetParameterBlockConstant(current.t);
    }

    for (int j = 1; j < 5; ++j) {
      if (i - j < 0) continue;
      Node& connected = nodes[static_cast<std::size_t>(i - j)];
      const Eigen::Vector3d relative_t =
          connected.vio_q.inverse() * (current.vio_t - connected.vio_t);
      const double relative_yaw = current.yaw - connected.yaw;
      problem.AddResidualBlock(
          FourDOFError::Create(relative_t.x(), relative_t.y(), relative_t.z(),
                               relative_yaw, connected.pitch, connected.roll),
          nullptr, &connected.yaw, connected.t, &current.yaw, current.t);
    }

    if (current.loop_index >= 0) {
      if (current.loop_index < first_index || current.loop_index >= current.index) {
        std::cerr << "loop endpoint outside optimization window\n";
        return 2;
      }
      Node& connected = nodes[static_cast<std::size_t>(current.loop_index - first_index)];
      problem.AddResidualBlock(
          FourDOFLoopError::Create(current.loop_t.x(), current.loop_t.y(),
                                   current.loop_t.z(), current.loop_yaw,
                                   connected.pitch, connected.roll, yaw_scale),
          loop_loss, &connected.yaw, connected.t, &current.yaw, current.t);
    }
  }

  ceres::Solver::Options options;
  options.linear_solver_type = ceres::SPARSE_NORMAL_CHOLESKY;
  options.max_num_iterations = 5;
  ceres::Solver::Summary summary;
  ceres::Solve(options, &problem, &summary);
  if (!summary.IsSolutionUsable()) {
    std::cerr << "Ceres returned unusable solution: " << summary.BriefReport() << "\n";
    return 3;
  }

  std::cout << std::setprecision(17);
  std::cout << "SUMMARY " << summary.initial_cost << " " << summary.final_cost
            << " " << summary.iterations.size() << "\n";
  for (const Node& n : nodes) {
    std::cout << "NODE " << n.index << " " << n.t[0] << " " << n.t[1] << " "
              << n.t[2] << " " << n.yaw << " " << n.pitch << " " << n.roll
              << "\n";
  }
  return 0;
}
