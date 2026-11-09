// Read-only clock diagnostic against the pinned RealSense SDK; no ROS/control outputs.
#include <librealsense2/rs.hpp>
#include <chrono>
#include <csignal>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <thread>
#include <vector>
static volatile std::sig_atomic_t stopped=0;
static void stop(int) { stopped=1; }
using Clock=std::chrono::steady_clock;
static int64_t system_ns() { return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::system_clock::now().time_since_epoch()).count(); }
static int64_t mono_ns() { return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count(); }
int main(int argc,char** argv) {
 if(argc!=4) { std::cerr<<"Usage: clock_probe SERIAL SECONDS OUTPUT.csv\n";return 2; }
 const double duration=std::stod(argv[2]);
 if(duration<=0 || duration>600) return 2;
 std::signal(SIGINT,stop);std::signal(SIGTERM,stop);
 std::ofstream out(argv[3]);if(!out) return 2;
 out<<std::setprecision(17)<<"kind,index,number,domain,sdk_ms,system_ns,monotonic_ns,raw_frame_ts,raw_sensor_ts,backend_ts,toa\n";
 std::mutex mutex;std::string error;
 rs2::context context;rs2::device selected;
 for(auto d:context.query_devices()) if(std::string(d.get_info(RS2_CAMERA_INFO_SERIAL_NUMBER))==argv[1]) selected=d;
 if(!selected) throw std::runtime_error("Expected exact camera serial is absent");
 struct Entry {rs2::sensor sensor;bool opened=false,started=false;};
 struct Option {rs2::sensor sensor;rs2_option option;float value;};
 std::vector<Entry> sensors;std::vector<Option> restore;
 auto cleanup=[&] {
  for(auto &s:sensors) if(s.started) {try{s.sensor.stop();s.started=false;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';error="stop failed";}}
  for(auto &s:sensors) if(s.opened) {try{s.sensor.close();s.opened=false;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';error="close failed";}}
  for(auto &o:restore) try{o.sensor.set_option(o.option,o.value);std::cout<<"restored "<<rs2_option_to_string(o.option)<<'='<<o.sensor.get_option(o.option)<<'\n';}catch(const std::exception&e){std::cerr<<e.what()<<'\n';error="option restore failed";}
 };
 try {
  std::map<std::pair<int,int>,bool> found;
  for(auto sensor:selected.query_sensors()) {
   std::vector<rs2::stream_profile> profiles;
   for(auto p:sensor.get_stream_profiles()) {
    auto kind=p.stream_type();bool wanted=false;
    if((kind==RS2_STREAM_GYRO && p.fps()==200)||(kind==RS2_STREAM_ACCEL && p.fps()==100)) wanted=true;
    if(auto v=p.as<rs2::video_stream_profile>())
     wanted=(v.width()==640 && v.height()==480 && p.fps()==15 &&
       ((kind==RS2_STREAM_INFRARED && (p.stream_index()==1 || p.stream_index()==2) && p.format()==RS2_FORMAT_Y8)||
        (kind==RS2_STREAM_DEPTH && p.format()==RS2_FORMAT_Z16)));
    auto key=std::make_pair(int(kind),p.stream_index());
    if(wanted && !found[key]) {found[key]=true;profiles.push_back(p);std::cout<<"profile "<<p.stream_name()<<' '<<p.stream_index()<<' '<<p.fps()<<' '<<p.format()<<'\n';}
   }
   if(profiles.empty()) continue;
   if(sensor.supports(RS2_OPTION_GLOBAL_TIME_ENABLED)) {restore.push_back({sensor,RS2_OPTION_GLOBAL_TIME_ENABLED,sensor.get_option(RS2_OPTION_GLOBAL_TIME_ENABLED)});sensor.set_option(RS2_OPTION_GLOBAL_TIME_ENABLED,1);}
   if(sensor.supports(RS2_OPTION_EMITTER_ENABLED)) {restore.push_back({sensor,RS2_OPTION_EMITTER_ENABLED,sensor.get_option(RS2_OPTION_EMITTER_ENABLED)});sensor.set_option(RS2_OPTION_EMITTER_ENABLED,0);}
   sensors.push_back({sensor});sensor.open(profiles);sensors.back().opened=true;
  }
  if(found.size()!=5) throw std::runtime_error("Exact five stream profiles unavailable");
  for(auto &s:sensors) {
   s.sensor.start([&](rs2::frame frame) {
    const auto system=system_ns(),mono=mono_ns();
    try {
     const auto profile=frame.get_profile();const auto stamp=frame.get_timestamp();const auto domain=frame.get_frame_timestamp_domain();
     std::lock_guard<std::mutex> guard(mutex);
     out<<rs2_stream_to_string(profile.stream_type())<<','<<profile.stream_index()<<','<<frame.get_frame_number()<<','<<rs2_timestamp_domain_to_string(domain)<<','<<stamp<<','<<system<<','<<mono;
     for(auto field:{RS2_FRAME_METADATA_FRAME_TIMESTAMP,RS2_FRAME_METADATA_SENSOR_TIMESTAMP,RS2_FRAME_METADATA_BACKEND_TIMESTAMP,RS2_FRAME_METADATA_TIME_OF_ARRIVAL}) {
      out<<',';if(frame.supports_frame_metadata(field)) out<<frame.get_frame_metadata(field);
     }
     out<<'\n';
    }catch(const std::exception&e){std::lock_guard<std::mutex> guard(mutex);error=e.what();stopped=1;}
   });s.started=true;
  }
  const auto start=Clock::now();
  while(!stopped && std::chrono::duration<double>(Clock::now()-start).count()<duration) {
   std::this_thread::sleep_for(std::chrono::milliseconds(100));
   std::lock_guard<std::mutex> guard(mutex);out.flush();if(!out) {error="output failure";break;}
  }
 }catch(const std::exception&e) {error=e.what();}
 cleanup();out.flush();
 if(!error.empty()){std::cerr<<error<<'\n';return 1;}
 std::cout<<"capture stopped; all owned streams closed\n";return 0;
}
