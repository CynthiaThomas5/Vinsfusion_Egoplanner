// Real vendor spline regression: feasibility scaling must cover short curves.
#include "bspline_opt/uniform_bspline.h"
#include <cassert>
#include <cmath>
#include <iostream>

int main() {
  for (int count : {6, 9, 20}) {
    Eigen::MatrixXd points(3, count);
    for (int i=0; i<count; ++i) {
      points(0,i)=0.24*i;
      points(1,i)=0.06*std::sin(i*.4);
      points(2,i)=0.01*i;
    }
    ego_planner::UniformBspline spline(points,3,.5);
    auto original=spline;
    spline.setPhysicalLimits(.2,.2,.05);
    double ratio=0.; assert(!spline.checkFeasibility(ratio,false));
    assert(std::isfinite(ratio) && ratio>1.);
    const double duration=spline.getTimeSum();
    spline.lengthenTime(ratio);
    assert(std::abs(spline.getTimeSum()-ratio*duration)<1e-9);
    double after=0.;assert(spline.checkFeasibility(after,false));
    for (int j=0; j<=100; ++j) {
      double t=duration*j/100.;
      assert((original.evaluateDeBoorT(t)-spline.evaluateDeBoorT(t*ratio)).norm()<1e-9);
      assert((original.getDerivative().evaluateDeBoorT(t)/ratio-spline.getDerivative().evaluateDeBoorT(t*ratio)).norm()<1e-9);
    }
    std::cout<<"PASS control_points="<<count<<" duration_ratio="<<ratio<<" feasible=1"<<std::endl;
  }
}
