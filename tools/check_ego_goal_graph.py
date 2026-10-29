#!/usr/bin/env python3
"""Validate control endpoints while allowing extra read-only topic subscribers."""
import re,sys
from pathlib import Path


def check_graph(text):
    endpoints=[]
    for block in re.split(r'(?=^Node name:)',text,flags=re.M):
        name=re.search(r'^Node name:\s*(\S+)',block,re.M)
        kind=re.search(r'^Endpoint type:\s*(\S+)',block,re.M)
        if name and kind:endpoints.append((name[1],kind[1]))
    publishers=[name for name,kind in endpoints if kind=='PUBLISHER']
    subscribers=[name for name,kind in endpoints if kind=='SUBSCRIPTION']
    return publishers==['uav_navigation'] and {'drone_0_ego_planner_node','uav_px4_bridge'}.issubset(subscribers)


if __name__=='__main__':
    raise SystemExit(0 if check_graph(Path(sys.argv[1]).read_text()) else 1)
