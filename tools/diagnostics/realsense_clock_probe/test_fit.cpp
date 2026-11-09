// Behavioral test against real SDK clock class, not a reimplementation of its fit.
#include "src/global_timestamp_reader.h"
#include <cmath>
#include <iostream>
int main() {
 librealsense::CLinearCoefficients fit(15);
 const double epoch=1700000000000.,slope=1.0004;
 for(int i=0;i<16;++i) {
  const double x=i*1000.;fit.update_last_sample_time(x);
  // One delayed USB exchange in a 16-sample drift window.
  fit.add_value(librealsense::CSample(x,epoch+slope*x+(i==13?20.:0.)));
 }
 const double error=fit.calc_value(17000.)-(epoch+slope*17000.);
 std::cout<<"single delayed exchange prediction error_ms="<<error<<'\n';
 if(std::fabs(error)>.1) return 1;
 return 0;
}
