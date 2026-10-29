"""Bind instantaneous physics endpoints to a run; never infer missing states."""
import hashlib
import json
import math

from n10_run_identity import read_run_identity


def instantaneous_endpoints(run, truth_rows):
    """Return copied truth rows with verified world velocities, or insufficiency."""
    evidence = {'status': 'INSUFFICIENT', 'instantaneous_endpoint_state_observed': False}
    try:
        if not truth_rows:
            raise ValueError('no_requested_physics_endpoints')
        report = json.loads((run / 'debug-truth-kinematics-observation.json').read_text())
        ledger = run / 'debug-truth-kinematics.jsonl'
        identity = read_run_identity(run)
        if not identity.get('complete') or report.get('run_identity') != identity:
            raise ValueError('kinematics_run_identity_mismatch_or_incomplete')
        if (report.get('schema') != 'uav-kinematics-observation/v1'
                or report.get('enabled') is not True
                or report.get('metadata_validated') is not True
                or report.get('error_count') != 0
                or report.get('subscribe_ok') is not True
                or report.get('safe_session_terminal_observed') is not True
                or report.get('terminal_flight_record_observed') is not True):
            raise ValueError('kinematics_observer_incomplete')
        payload = ledger.read_bytes()
        if hashlib.sha256(payload).hexdigest() != report.get('record_sha256'):
            raise ValueError('kinematics_ledger_hash_mismatch')
        manifest = json.loads((run / 'n09-contact-model-manifest.json').read_text())
        model_source = json.loads((run / 'n10-px4-model-source.json').read_text())
        plugin = manifest.get('kinematics_observer') or {}
        files = json.loads((run / 'runtime-contract.json').read_text()).get('files', {})
        expected = {'enabled': True, 'plugin_filename': 'libuav_truth_kinematics.so',
                    'plugin_class': 'uav::debug_truth::ModelKinematics',
                    'topic': '/debug_truth/model_kinematics', 'pose_reference': 'model_origin',
                    'velocity_frame': 'world', 'velocity_kind': 'instantaneous_physics_components'}
        if any(plugin.get(k) != v for k, v in expected.items()):
            raise ValueError('kinematics_plugin_contract_mismatch')
        overlay_root = manifest.get('overlay_root')
        generated_models = manifest.get('generated_model_sha256') or {}
        expected_model_sha = generated_models.get('x500_d435i/model.sdf')
        selected_model = str(model_source.get('selected_model_sdf') or '')
        model_root = str(model_source.get('px4_gz_models') or '')
        expected_selected_model = f'{model_root.rstrip("/")}/x500_d435i/model.sdf'
        overlay_model = run / 'n09-contact-models/x500_d435i/model.sdf'
        if (model_source.get('schema') != 'n10-px4-gazebo-model-source/v1'
                or model_source.get('model_name') != 'x500_d435i'
                or model_source.get('kinematics_requested') is not True
                or model_source.get('kinematics_plugin_entries') != 1
                or model_source.get('kinematics_plugin_source_present') is not True
                or not overlay_root or model_root != overlay_root
                or selected_model != expected_selected_model
                or expected_model_sha is None
                or model_source.get('selected_model_sdf_sha256') != expected_model_sha
                or not overlay_model.is_file()
                or hashlib.sha256(overlay_model.read_bytes()).hexdigest() != expected_model_sha):
            raise ValueError('kinematics_selected_model_source_mismatch')
        for field, path in (
                ('plugin_binary_sha256', 'install/uav_debug_truth/lib/libuav_truth_kinematics.so'),
                ('plugin_source_sha256', 'src/own/uav_debug_truth/src/model_kinematics.cpp')):
            digest = plugin.get(field)
            if not isinstance(digest, str) or len(digest) != 64 or files.get(path) != digest:
                raise ValueError('kinematics_plugin_runtime_hash_mismatch')
        rows = [json.loads(line) for line in payload.splitlines() if line.strip()]
        if len(rows) != report.get('record_count') or not rows:
            raise ValueError('kinematics_record_count_mismatch')
        stamps = [int(row['stamp_ns']) for row in rows]
        if any(b <= a for a, b in zip(stamps, stamps[1:])):
            raise ValueError('kinematics_nonmonotonic_source')
        models = {row.get('model_name') for row in rows}
        if len(models) != 1 or not next(iter(models)):
            raise ValueError('kinematics_model_identity_changed')
        by_stamp = dict(zip(stamps, rows))
        converted = []
        for truth in truth_rows:
            row = by_stamp.get(int(truth['stamp_ns']))
            if row is None:
                raise ValueError('kinematics_missing_physics_endpoint')
            if row.get('schema') != 'uav-model-kinematics/v1' or row.get('pose_reference') != 'model_origin':
                raise ValueError('kinematics_endpoint_reference_mismatch')
            for field, size in (('xyz', 3), ('q_xyzw', 4),
                                ('linear_velocity_world_m_s', 3), ('angular_velocity_world_rad_s', 3)):
                values = row.get(field, [])
                if len(values) != size or not all(math.isfinite(v) for v in values):
                    raise ValueError('kinematics_invalid_endpoint')
            if abs(sum(v*v for v in row['q_xyzw']) - 1) > 2e-5:
                raise ValueError('kinematics_invalid_quaternion')
            if max(abs(a-b) for a, b in zip(row['xyz'], truth['xyz'])) > 1e-8:
                raise ValueError('kinematics_model_origin_pose_mismatch')
            # Quaternion sign has no physical meaning.
            q_error = min(max(abs(a-sign*b) for a, b in zip(row['q_xyzw'], truth['q_xyzw']))
                          for sign in (-1, 1))
            if q_error > 1e-8:
                raise ValueError('kinematics_orientation_mismatch')
            converted.append({**truth,
                'linear_velocity_xyz_m_s': row['linear_velocity_world_m_s'],
                'angular_velocity_xyz_rad_s': row['angular_velocity_world_rad_s']})
        evidence.update(status='PASS', instantaneous_endpoint_state_observed=True,
                        endpoint_count=len(converted), record_sha256=report['record_sha256'],
                        plugin_identity=plugin, velocity_frame='world', pose_reference='model_origin',
                        selected_model_sdf_sha256=expected_model_sha,
                        selected_model_sdf=selected_model)
        return converted, evidence
    except (OSError, ValueError, KeyError, TypeError) as exc:
        evidence['reason'] = f'{type(exc).__name__}:{exc}'
        return None, evidence
