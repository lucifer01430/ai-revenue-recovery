def diagnose_and_recommend(payment_data):
    """
    Mock AI engine that returns a structured diagnosis and recommendation.
    In a real app, this would call an LLM (e.g., OpenAI, Anthropic).
    """
    error_code = payment_data.get('error_code', '')
    error_description = payment_data.get('error_description', '').lower()
    
    # Simple heuristic to simulate AI decision
    if 'insufficient' in error_description or error_code == 'BAD_REQUEST_ERROR':
        diagnosis = 'Customer has insufficient funds.'
        recommendation = 'retry' # Let's say we retry later
    elif 'expired' in error_description:
        diagnosis = 'Card has expired.'
        recommendation = 'payment_link'
    elif 'fraud' in error_description:
        diagnosis = 'High risk of fraud.'
        recommendation = 'stop'
    else:
        diagnosis = 'Unknown failure reason.'
        recommendation = 'escalate'

    return {
        'diagnosis': diagnosis,
        'recommendation': recommendation,
        'confidence': 0.85
    }
