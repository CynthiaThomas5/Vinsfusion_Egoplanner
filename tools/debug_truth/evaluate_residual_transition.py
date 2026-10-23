#!/usr/bin/env python3
"""Offline attribution of recorded Ceres costs; not physical noise calibration."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

GROUPS = ('marginalization', 'imu', 'visual')


def decompose(metric):
    c = metric.get('cost_components')
    if not isinstance(c, dict) or c.get('evaluation_ok') is not True:
        raise ValueError('Missing successful group evaluation')
    total, count = float(metric['final_cost']), int(metric['residual_components'])
    if not math.isfinite(total) or total < 0 or count <= 0:
        raise ValueError('Invalid total cost/count')
    rows = {}
    for name in GROUPS:
        group = c[name]; value, n = float(group['cost']), int(group['residual_components'])
        if not math.isfinite(value) or value < 0 or n < 0:
            raise ValueError('Invalid group cost/count')
        rows[name] = {'cost': value, 'residual_components': n,
                      'normalized_squared_contribution': 2*value/count,
                      'group_normalized_cost': math.sqrt(2*value/n) if n else None,
                      'cost_fraction': value/total if total else 0.0}
    discrepancy = sum(p['cost'] for p in rows.values())-total
    if abs(discrepancy) > 1e-5*max(1.0,total) or sum(p['residual_components'] for p in rows.values()) != count:
        raise ValueError('Residual groups do not reproduce solver total')
    return {'source_ns': int(metric['stamp_ns']), 'normalized_cost': math.sqrt(2*total/count),
            'groups': rows, 'evaluation_seconds': c['evaluation_seconds'],
            'cost_sum_error': discrepancy, 'input_features': metric['input_features'],
            'stereo_features': metric['stereo_features'], 'continued_tracks': metric['continued_tracks'],
            'long_tracks': metric['long_tracks']}


def total_transition(previous_cost, previous_count, current_cost, current_count):
    if any(not math.isfinite(v) or v < 0 for v in [previous_cost,current_cost]) or min(previous_count,current_count)<=0:
        raise ValueError('Invalid transition totals')
    return {'previous_cost':previous_cost,'current_cost':current_cost,
            'previous_count':previous_count,'current_count':current_count,
            'cost_change_contribution':2*(current_cost-previous_cost)/current_count,
            'residual_count_change_contribution':2*previous_cost*(1/current_count-1/previous_count),
            'total_squared_cost_change':2*current_cost/current_count-2*previous_cost/previous_count}


def transition(previous, current):
    np = sum(p['residual_components'] for p in previous['groups'].values())
    nc = sum(p['residual_components'] for p in current['groups'].values())
    cp = sum(p['cost'] for p in previous['groups'].values())
    numerator = {name: 2*(current['groups'][name]['cost']-previous['groups'][name]['cost'])/nc for name in GROUPS}
    denominator = 2*cp*(1/nc-1/np)
    return {'cost_change_contribution': numerator, 'residual_count_change_contribution': denominator,
            'previous_total_components': np, 'current_total_components': nc,
            'total_squared_cost_change': current['normalized_cost']**2-previous['normalized_cost']**2}


def evaluate(run):
    load=lambda n:json.loads((run/n).read_text())
    flight=load('flight.json'); metrics=flight['vins_quality_history']
    stamps=[p['stamp_ns'] for p in metrics]
    if any(b<=a for a,b in zip(stamps,stamps[1:])):
        raise ValueError('Nonmonotonic telemetry; no sorting or session stitching')
    rows=[decompose(p) for p in metrics if p.get('solve_current') and p.get('cost_components') is not None]
    if not rows:
        raise ValueError('No actual group diagnostics recorded')
    root=Path(__file__).resolve().parents[2]
    policy=json.loads((root/'config/components/localization/health.json').read_text())
    limit=policy['max_normalized_cost']
    failures=[p for p in flight['localization_quality_history'] if p['reason']=='normalized_cost_exceeded']
    trigger=None
    if failures:
        # Status may follow the solver source stamp; identify the first recorded crossing at/before that status.
        eligible=[p for p in rows if p['source_ns']<=failures[0]['stamp_ns'] and p['normalized_cost']>limit]
        if not eligible: raise ValueError('Health crossing lacks corresponding diagnostic source frame')
        trigger=eligible[0]
    start=(flight.get('goal') or {}).get('source_ns')
    previous=None; delta=None
    if trigger:
        before=[p for p in rows if p['source_ns']<trigger['source_ns']]
        previous=before[-1] if before else None
        if previous:
            delta={name:trigger['groups'][name]['normalized_squared_contribution']-previous['groups'][name]['normalized_squared_contribution'] for name in GROUPS}
    previous_metric=None; trigger_metric=None
    if trigger:
        trigger_metric=next(p for p in metrics if p['stamp_ns']==trigger['source_ns'])
        prior_metrics=[p for p in metrics if p['solve_current'] and p['stamp_ns']<trigger['source_ns']]
        previous_metric=prior_metrics[-1] if prior_metrics else None
    durations=[p['evaluation_seconds'] for p in rows]
    report={'scope':__doc__,'run_id':run.name,'epoch':flight.get('localization_epoch'),
            'mission_result':flight['result'],'mission_failure':flight.get('failure'),
            'landed_and_disarmed':flight.get('landed_and_disarmed',False),
            'diagnostic_mode':load('vins-diagnostics.json'),'diagnostic_frames':len(rows),
            'health_limit_unchanged':limit,'quality_crossing_observed':trigger is not None,
            'trigger':trigger,'previous':previous,'trigger_squared_contribution_change':delta,
            'previous_solver_total':{k:previous_metric[k] for k in ['stamp_ns','final_cost','residual_components']} if previous_metric else None,
            'trigger_total_transition':total_transition(previous_metric['final_cost'],previous_metric['residual_components'],trigger_metric['final_cost'],trigger_metric['residual_components']) if previous_metric else None,
            'trigger_numerator_denominator_decomposition':transition(previous,trigger) if previous else None,
            'largest_trigger_cost_group':max(GROUPS,key=lambda n:trigger['groups'][n]['cost']) if trigger else None,
            'largest_positive_spike_group':max(delta,key=delta.get) if delta and max(delta.values())>0 else None,
            'return_goal_source_ns':start if flight.get('active_leg_index',0)>=1 else None,
            'trigger_relative_to_current_goal_sim_s':(trigger['source_ns']-start)/1e9 if trigger and start else None,
            'diagnostic_evaluation_seconds':{'maximum':max(durations),'mean':sum(durations)/len(durations)},
            'max_absolute_group_sum_error':max(abs(p['cost_sum_error']) for p in rows),
            'input_sha256':{n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in ['flight.json','vins-diagnostics.json']},
            'limitations':['Cost groups are whitened/robust objective terms; magnitudes are not pixel or metre errors.',
                           'Dominant marginalization cost does not identify which historical measurements caused the prior.',
                           'Continuous diagnostic evaluation can perturb scheduling; evaluate overhead and retain failures.',
                           'Attribution is not evidence to loosen a threshold or clear a locked session.']}
    if trigger and (run/'odometry-errors.csv').exists():
        errors=list(csv.DictReader((run/'odometry-errors.csv').open()))
        match=next((p for p in errors if abs(int(p['source_ns'])-trigger['source_ns'])<=2),None)
        report['trigger_independent_error'] = ({'source_ns':int(match['source_ns']),
            'position_error_m':float(match['position_error_m']),
            'yaw_error_deg':float(match['yaw_error_deg'])} if match else None)
        report['input_sha256']['odometry-errors.csv']=hashlib.sha256((run/'odometry-errors.csv').read_bytes()).hexdigest()
    return report,rows


def plot(run, report, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    trigger=report['trigger'];center=trigger['source_ns'] if trigger else (report['return_goal_source_ns'] or rows[-1]['source_ns'])
    selected=[p for p in rows if -5<=(p['source_ns']-center)/1e9<=8]
    if not selected: selected=rows
    t=[(p['source_ns']-center)/1e9 for p in selected]
    fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True)
    style='.-' if len(selected)<10 else '-'
    for name in GROUPS:
        axes[0].plot(t,[p['groups'][name]['normalized_squared_contribution'] for p in selected],style,label=name)
    axes[0].set_ylabel('Contribution to normalized cost²');axes[0].legend()
    metrics=json.loads((run/'flight.json').read_text())['vins_quality_history']
    context=[p for p in metrics if p.get('solve_current') and p['residual_components']>0 and -5<=(p['stamp_ns']-center)/1e9<=8]
    ct=[(p['stamp_ns']-center)/1e9 for p in context]
    axes[1].plot(ct,[math.sqrt(2*p['final_cost']/p['residual_components']) for p in context]);axes[1].axhline(report['health_limit_unchanged'],c='red',ls='--');axes[1].set_ylabel('Normalized total cost')
    for key in ['input_features','stereo_features','continued_tracks','long_tracks']:
        axes[2].plot(ct,[p[key] for p in context],label=key)
    axes[2].set(ylabel='Feature count',xlabel='Simulation seconds from health crossing (or diagnostic reference)');axes[2].legend()
    for ax in axes:
        ax.grid(alpha=.2);ax.axvline(0,c='grey',ls=':')
        if trigger:ax.axvline((trigger['source_ns']-center)/1e9,c='red',ls=':')
    fig.suptitle('Recorded residual contributions and track counts');fig.tight_layout()
    fig.savefig(run/'residual-transition.png',dpi=160);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--plot',action='store_true');a=p.parse_args()
    report,rows=evaluate(a.run)
    (a.run/'residual-transition.json').write_text(json.dumps(report,indent=2)+'\n')
    if a.plot:plot(a.run,report,rows)
    print(json.dumps(report,indent=2))
