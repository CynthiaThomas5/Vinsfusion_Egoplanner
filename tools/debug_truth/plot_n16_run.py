#!/usr/bin/env python3
"""Standalone measured resource/queue/latency/VIO curves, without numeric gates."""
import argparse,csv,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(run):
    run=Path(run);flight=json.loads((run/'flight.json').read_text());resource=json.loads((run/'n10-resource-observation.json').read_text())
    window=flight.get('continuous_navigation') or {};start=window.get('start_source_ns',flight['goal_start_sim_ns']);end=window.get('end_source_ns',flight['goal_completed_source_ns'])
    samples=[r for r in resource['samples'] if isinstance(r.get('sim_ns'),int) and start<=r['sim_ns']<=end]
    native=[json.loads(s) for s in (run/'n10-vins-queue-telemetry.jsonl').read_text().splitlines() if s.strip()]
    native=[r for r in native if start<=r['source_stamp_ns']<=end]
    fig,axes=plt.subplots(4,1,figsize=(11,10),sharex=True)
    cpu=[]
    for a,b in zip(samples,samples[1:]):
        dt=b['wall_elapsed_s']-a['wall_elapsed_s']
        if dt>0:cpu.append(((b['sim_ns']-start)/1e9,(b['cgroup']['cpu_stat']['usage_usec']-a['cgroup']['cpu_stat']['usage_usec'])/1e6/dt))
    if cpu:axes[0].plot(*zip(*cpu));axes[0].set_ylabel('CPU cores used')
    axes[1].plot([(r['sim_ns']-start)/1e9 for r in samples],[float(r['cgroup']['memory_current'])/2**30 for r in samples]);axes[1].set_ylabel('Memory GiB')
    for name,label in [('waiting_features','Waiting features'),('pending_feature_span_ns','Pending span (s)')]:
        pairs=[((r['source_stamp_ns']-start)/1e9,r['queue_metrics']['work'][name]/(1e9 if name.endswith('_ns') else 1)) for r in native]
        if pairs:axes[2].plot(*zip(*pairs),label=label)
    axes[2].legend();axes[2].set_ylabel('Pending work')
    lags=[((r['source_stamp_ns']-start)/1e9,(r['queue_metrics']['work']['latest_imu_before_ns']-r['queue_metrics']['work']['interval_endpoint_ns'])/1e9) for r in native]
    receipts=[((r['source_stamp_ns']-start)/1e9,(r['sim_ns_at_receipt']-r['source_stamp_ns'])/1e9) for r in native if isinstance(r.get('sim_ns_at_receipt'),int)]
    if lags:axes[3].plot(*zip(*lags),label='Native work lag')
    if receipts:axes[3].plot(*zip(*receipts),label='Telemetry source-to-receipt sim age',alpha=.6)
    axes[3].legend();axes[3].set_ylabel('Seconds');axes[3].set_xlabel('Mission simulation seconds')
    for ax in axes:ax.grid(alpha=.25)
    scope='continuous mission' if window else 'short archive format replay; no N16 credit'
    fig.suptitle(f'{run.name}: {scope}');fig.tight_layout();resource_plot=run/'n16-resource-queue-latency.png';fig.savefig(resource_plot,dpi=140);plt.close(fig)
    files=[resource_plot]
    errorfile=run/'odometry-errors.csv'
    if errorfile.exists():
        with errorfile.open() as stream:rows=[r for r in csv.DictReader(stream) if start<=int(r['source_ns'])<=end]
        fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True)
        times=[(int(r['source_ns'])-start)/1e9 for r in rows]
        axes[0].plot(times,[float(r['position_error_m']) for r in rows]);axes[0].set_ylabel('VIO position error m')
        axes[1].plot(times,[float(r['yaw_error_deg']) for r in rows]);axes[1].set_ylabel('VIO yaw error deg')
        for key in ['truth_x_m','truth_y_m','truth_z_m']:axes[2].plot(times,[float(r[key]) for r in rows],label=key)
        axes[2].legend();axes[2].set_ylabel('Actual IMU position m');axes[2].set_xlabel('Mission simulation seconds')
        for ax in axes:ax.grid(alpha=.25)
        fig.suptitle(run.name);fig.tight_layout();file=run/'n16-vio-and-actual-motion.png';fig.savefig(file,dpi=140);plt.close(fig);files.append(file)
    report={'schema':'n16-measured-plots/v1','scope':scope,'start_ns':start,'end_ns':end,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'control_effect':False}
    (run/'n16-plot-manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args();print(json.dumps(plot(a.run)))
