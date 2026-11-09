// Diagnostic copy of global_timestamp_reader::get_frame_timestamp from
// librealsense bf2778061d5dd29776e9aca8765f75852671760b, Apache-2.0.
// Copyright (c) 2015 RealSense, Inc. All Rights Reserved.
// Only this probe process preloads it. Original conversion arithmetic is retained.
#include "src/global_timestamp_reader.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <mutex>
namespace librealsense {
rs2_time_t global_timestamp_reader::get_frame_timestamp(const std::shared_ptr<frame_interface>& frame) {
 const double raw=_device_timestamp_reader->get_frame_timestamp(frame);
 double converted=raw;
 const auto domain=_device_timestamp_reader->get_frame_timestamp_domain(frame);
 if(_option_is_enabled->is_true() && domain==RS2_TIMESTAMP_DOMAIN_HARDWARE_CLOCK) {
  auto sp=_time_diff_keeper.lock();
  if(sp) converted=sp->get_system_hw_time(raw,_ts_is_ready);
 }
 const auto system=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
 static std::mutex lock;std::lock_guard<std::mutex> guard(lock);
 static FILE* file=[](){const char* p=std::getenv("HW_CLOCK_TRACE");if(!p) return static_cast<FILE*>(nullptr);FILE* f=std::fopen(p,"w");if(f) {std::fputs("reader,frame,raw_domain,raw_ms,converted_ms,system_ns,ready\n",f);std::setvbuf(f,nullptr,_IOLBF,0);}return f;}();
 if(file) std::fprintf(file,"%p,%p,%d,%.17g,%.17g,%lld,%d\n",static_cast<void*>(this),static_cast<void*>(frame.get()),int(domain),raw,converted,static_cast<long long>(system),int(_ts_is_ready));
 return converted;
}
}

// Same pinned update arithmetic plus a separate diagnostic record of fit inputs.
namespace librealsense {
bool time_diff_keeper::update_diff_time() {
 try {
  if(!_users_count) throw wrong_api_call_sequence_exception("update_diff_time before start");
  using namespace std::chrono;
  const double start=duration<double,std::milli>(system_clock::now().time_since_epoch()).count();
  const double hardware=_device->get_device_time_ms();
  const double finish=duration<double,std::milli>(system_clock::now().time_since_epoch()).count();
  const double half=(finish-start)/2;
  std::lock_guard<std::recursive_mutex> guard(_read_mtx);
  const double old_min=_min_command_delay;
  if(half<_min_command_delay) {_coefs.add_const_y_coefs(half-_min_command_delay);_min_command_delay=half;}
  const double assigned=finish-_min_command_delay;
  if(_is_ready) _coefs.update_samples_base(hardware);
  _coefs.add_value(CSample(hardware,assigned));_is_ready=true;
  static FILE* file=[](){const char* p=std::getenv("HW_FIT_TRACE");if(!p)return static_cast<FILE*>(nullptr);FILE* f=std::fopen(p,"w");if(f){std::fputs("keeper,start_ms,finish_ms,hardware_ms,half_ms,old_min_half_ms,min_half_ms,assigned_ms,predicted_ms\n",f);std::setvbuf(f,nullptr,_IOLBF,0);}return f;}();
  if(file)std::fprintf(file,"%p,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",static_cast<void*>(this),start,finish,hardware,half,old_min,_min_command_delay,assigned,_coefs.calc_value(hardware));
  return true;
 }catch(const std::exception& e){std::fprintf(stderr,"fit probe: %s\n",e.what());return false;}
}
}
