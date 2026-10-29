"""Small ROS-free helpers for preserving N08 action terminal results."""


def summarize_navigation_action_result(wrapped):
    """Return the action status and task-level result fields as JSON values."""
    result = wrapped.result
    return {
        'status': int(wrapped.status),
        'success': bool(result.success),
        'outcome': str(result.outcome),
        'reason': str(result.reason),
    }
