// Standalone tests of the exact production raw-voxel query (no ROS or truth).
#include <plan_env/sphere_query.h>
#include <cassert>
#include <limits>
#include <iostream>
int main()
{
  using plan_env::querySphere;
  const std::array<double, 3> origin{0,0,0}, extent{10,10,10}, center{5,5,5};
  const std::array<int, 3> size{100,100,100};
  auto free = [](int, int, int) { return 0; };
  auto query = [&](std::array<double, 3> p, double r, auto f) {
    return querySphere(p, r, origin, extent, size, .1, f);
  };
  auto result = query(center, .5, free);
  assert(result.accepted && result.reason == "free" && result.free > 0);
  result = query(center, .5, [](int, int, int) { return -1; });
  assert(result.accepted && result.reason == "unknown" && result.unknown > 0);
  result = query(center, .5, [](int x, int, int) { return x == 50 ? 1 : -1; });
  assert(result.reason == "occupied" && result.unknown > 0 && result.occupied > 0);
  // Sphere touches x=5 face: cell49 has a center outside the tiny sphere.
  result = query({5.05, 5.05, 5.05}, .05, [](int x, int, int) { return x == 49 ? 1 : 0; });
  assert(result.reason == "occupied");
  assert(query({.5,5,5}, .5, free).reason == "outside_map");
  assert(query({9.5,5,5}, .5, free).reason == "outside_map");
  assert(query(center, 0, free).reason == "invalid_query");
  assert(query(center, -1, free).reason == "invalid_query");
  assert(query(center, 2.1, free).reason == "invalid_query");
  assert(query({NAN,5,5}, .5, free).reason == "invalid_query");
  assert(query(center, NAN, free).reason == "invalid_query");
  assert(querySphere(center, .5, origin, extent, {10000,10000,10000}, .001, free).reason == "query_too_large");
  // Corner of a bounding-box cell outside the sphere must not reject it.
  result = query(center, .5, [](int x, int y, int z) {
    return x == 45 && y == 45 && z == 45 ? 1 : 0;
  });
  assert(result.reason == "free");
  std::cout << "PASS: free/unknown/occupied, intersecting face, outside, invalid and bounded queries\n";
}
