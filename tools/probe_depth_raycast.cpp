// Exact cell/segment checks for the production depth ray walker.
#include <plan_env/raycast.h>
#include <array>
#include <cassert>
#include <cmath>
#include <iostream>
#include <random>
#include <set>
using Cell = std::array<int,3>;
std::set<Cell> trace(Eigen::Vector3d start, Eigen::Vector3d end)
{
  RayCaster ray; ray.setInput(start,end); Eigen::Vector3d p;
  std::set<Cell> cells;
  for(int steps=0; ray.step(p); ++steps)
  {
    assert(steps<1000);
    cells.insert({int(p.x()),int(p.y()),int(p.z())});
  }
  return cells;
}
bool intersects(Eigen::Vector3d a, Eigen::Vector3d b, Cell c)
{
  double low=0, high=1;
  for(int axis=0;axis<3;++axis)
  {
    const double delta=b[axis]-a[axis];
    if(std::abs(delta)<1e-12)
    {
      if(a[axis]<c[axis] || a[axis]>c[axis]+1) return false;
    }
    else
    {
      double t1=(c[axis]-a[axis])/delta, t2=(c[axis]+1-a[axis])/delta;
      if(t1>t2) std::swap(t1,t2);
      low=std::max(low,t1);high=std::min(high,t2);
    }
  }
  return high-low>1e-10;
}
int main()
{
  std::mt19937 rng(63);std::uniform_real_distribution<double> random(-4.,4.);
  int incorrect=0, missing=0;
  bool divergent_intersection=false;
  std::set<Cell> visited;
  const Eigen::Vector3d camera(.17,.23,.31);
  for(int trial=0;trial<250;++trial)
  {
    Eigen::Vector3d end(random(rng),random(rng),random(rng));
    auto cells=trace(camera,end);
    Cell endcell{int(std::floor(end.x())),int(std::floor(end.y())),int(std::floor(end.z()))};
    for(auto cell:cells) if(!intersects(camera,end,cell)) ++incorrect;
    for(int x=-4;x<=4;++x)for(int y=-4;y<=4;++y)for(int z=-4;z<=4;++z)
    {
      Cell c{x,y,z};
      if(c!=endcell && intersects(camera,end,c) && !cells.count(c)) ++missing;
    }
    // Simulate the old traversal stopping at its first shared cell, from hit to camera.
    RayCaster ray;ray.setInput(end,camera);Eigen::Vector3d p;bool cut=false;
    while(ray.step(p))
    {
      Cell c{int(p.x()),int(p.y()),int(p.z())};
      if(cut && !visited.count(c)) divergent_intersection=true;
      if(visited.count(c)) cut=true;
      else if(!cut) visited.insert(c);
    }
  }
  std::cout << "incorrect=" << incorrect << " missing=" << missing
            << " intersecting rays diverge=" << divergent_intersection << std::endl;
  assert(incorrect==0 && missing==0);
  assert(divergent_intersection);
  // Parallel axes and negative movement starting exactly on a cell face.
  auto axis=trace({0.,.5,.5},{-3.2,.5,.5});
  assert(axis.count({-1,0,0}) && axis.count({-2,0,0}) && axis.count({-3,0,0}));
  std::cout << "PASS: exact random/axis ray traversal; shared cell does not imply shared suffix\n";
}
