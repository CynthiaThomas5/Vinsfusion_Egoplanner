"""Offline surface error policy, including legacy numeric gates."""
import math

def surface_error_result(values, thresholds, evidence_complete=True):
    values=list(values)
    valid=bool(values) and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0 for v in values)
    limit=thresholds.get("surface_center_error_sample_max_m")
    if limit is not None and (not isinstance(limit,(int,float)) or isinstance(limit,bool) or not math.isfinite(limit) or limit<0):
        raise ValueError("invalid surface error threshold")
    maximum=max(values) if valid else None
    status=("FAIL" if valid and limit is not None and maximum>limit else
            "PASS" if valid and evidence_complete else "INSUFFICIENT")
    return {"status":status,"maximum_observed_error_m":maximum,"threshold_m":limit,
            "numeric_limit_enabled":limit is not None,"measurement_status":"OBSERVED" if valid else "INSUFFICIENT",
            "measurement_count":len(values),"evidence_complete":bool(evidence_complete)}
