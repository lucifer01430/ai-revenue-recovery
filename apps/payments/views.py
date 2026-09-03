import json
import hmac
import hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from apps.recovery.services import process_failed_payment

@csrf_exempt
def razorpay_webhook(request):
    if request.method == 'POST':
        # Verify signature
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        if webhook_signature:
            secret = settings.RAZORPAY_WEBHOOK_SECRET
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                request.body,
                hashlib.sha256
            ).hexdigest()
            
            # Simple equal check for MVP (in production use hmac.compare_digest)
            if not hmac.compare_digest(expected_signature, webhook_signature):
                return JsonResponse({'error': 'Invalid signature'}, status=400)

        try:
            payload = json.loads(request.body)
            event_type = payload.get('event')
            
            if event_type == 'payment.failed':
                payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
                process_failed_payment(payment_entity)
                
            return JsonResponse({'status': 'ok'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

