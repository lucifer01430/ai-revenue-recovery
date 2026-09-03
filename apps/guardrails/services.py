def validate_action(recovery_case, recommendation):
    """
    Deterministic rule engine that intercepts AI recommendations.
    """
    # Rule 1: Max retries
    if recommendation == 'retry' and recovery_case.retries_attempted >= 3:
        return {
            'approved': False,
            'modified_recommendation': 'escalate',
            'reason': 'Max retries (3) exceeded.'
        }
    
    # Rule 2: Cannot retry fraud
    if 'fraud' in str(recovery_case.latest_diagnosis).lower() and recommendation == 'retry':
        return {
            'approved': False,
            'modified_recommendation': 'stop',
            'reason': 'Cannot retry a fraudulent transaction.'
        }
    
    return {
        'approved': True,
        'modified_recommendation': recommendation,
        'reason': 'Passed all rules.'
    }
