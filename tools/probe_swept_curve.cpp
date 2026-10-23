#include <plan_env/swept_curve.h>
#include <plan_env/sphere_query.h>
#include <cassert>
#include <bspline_opt/uniform_bspline.h>
#include <iostream>
using namespace plan_env;
int main()
{
  const std::array<double,3> origin{0,0,0}, extent{10,10,10};
  const std::array<int,3> size{100,100,100};
  auto curve=[](double t) { return std::array<double,3>{1+t,5,5}; };
  auto test=[&](auto classify) {
    return certifySweep(0,8,1,.1,.1,curve,[&](auto center,double r) {
      return querySphere(center,r,origin,extent,size,.1,classify);
    });
  };
  auto free=[](int,int,int) { return 0; };
  assert(test(free).free);
  // An obstacle and unknown space in the last third must both fail.
  assert(!test([](int x,int,int) { return x==85 ? 1:0; }).free);
  assert(!test([](int x,int,int) { return x==85 ? -1:0; }).free);
  // Obstacle lies exactly at the terminal point, and between sample centers.
  assert(!test([](int x,int,int) { return x==90 ? 1:0; }).free);
  auto queryfree=[](auto,double) { SphereQueryResult r;r.accepted=true;r.reason="free";return r; };
  assert(certifySweep(1,1,0,.1,.1,curve,queryfree).free);
  assert(!certifySweep(0,1,-1,.1,.1,curve,queryfree).free);
  assert(!certifySweep(0,1,NAN,.1,.1,curve,queryfree).free);
  assert(!certifySweep(0,1e9,1,.1,.1,curve,queryfree).free);
  // Directly verify the covering inequality for a curved, bounded-speed arc.
  const double speed=std::sqrt(2.);
  auto arc=[](double t) { return std::array<double,3>{t,std::sin(t),0}; };
  auto cover=[&](auto p,double radius) {
    SphereQueryResult out;out.accepted=true;out.reason="free";
    // Query radius includes body .1 plus a positive gap bound.
    assert(radius>.1);
    const double half_dt=(radius-.1)/speed;
    for(int k=0;k<=20;++k)
    {
      const auto q=arc(p[0]+(2.*k/20.-1)*half_dt);
      const double dx=q[0]-p[0],dy=q[1]-p[1];
      assert(std::sqrt(dx*dx+dy*dy)<=radius-.1+1e-12);
    }
    return out;
  };
  assert(certifySweep(0,3.1,speed,.1,.1,arc,cover).free);
  Eigen::MatrixXd points(3,13);
  for(int i=0;i<13;++i) points.col(i)<<1+i*.3,5+.2*std::sin(i),5;
  ego_planner::UniformBspline spline(points,3,.2);
  auto velocity=spline.getDerivative();
  const double bound=velocity.getControlPoint().colwise().norm().maxCoeff();
  for(int i=0;i<=1000;++i)
    assert(velocity.evaluateDeBoorT(spline.getTimeSum()*i/1000.).norm()<=bound+1e-12);
  const auto sweep=certifySweep(0,spline.getTimeSum(),bound,.1,.1,
      [&](double t) { auto p=spline.evaluateDeBoorT(t);return std::array<double,3>{p(0),p(1),p(2)}; }, queryfree);
  assert(sweep.free);
  std::cout<<"PASS: full curve, last third, endpoint, gaps, invalid and bounded work\n";
}
