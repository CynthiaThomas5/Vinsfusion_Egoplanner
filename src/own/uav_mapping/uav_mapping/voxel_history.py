"""Bounded union of historical occupied observations; never a planning map."""
import math


class VoxelHistory:
    def __init__(self, resolution, origin, size, capacity):
        if (not math.isfinite(resolution) or resolution <= 0
                or len(origin) != 3 or len(size) != 3
                or not all(math.isfinite(v) for v in (*origin, *size))
                or any(v <= 0 for v in size)
                or type(capacity) is not int or capacity <= 0):
            raise ValueError('invalid voxel history bounds')
        self.resolution = resolution
        self.origin = tuple(origin)
        self.size = tuple(size)
        self.capacity = capacity
        self.voxels = set()
        self.rejected_new_voxels = 0

    def clear(self):
        self.voxels.clear()
        self.rejected_new_voxels = 0

    def add(self, points):
        for point in points:
            if len(point) != 3 or not all(math.isfinite(v) for v in point):
                continue
            if not all(self.origin[i] <= point[i] < self.origin[i]+self.size[i]
                       for i in range(3)):
                continue
            index = tuple(math.floor((point[i]-self.origin[i])/self.resolution)
                          for i in range(3))
            if index in self.voxels:
                continue
            if len(self.voxels) >= self.capacity:
                self.rejected_new_voxels += 1
                continue
            self.voxels.add(index)

    def centers(self):
        return [tuple(self.origin[i]+(cell[i]+.5)*self.resolution for i in range(3))
                for cell in sorted(self.voxels)]
