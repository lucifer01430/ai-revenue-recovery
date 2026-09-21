import hashlib
import hmac
import json

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from apps.payments.models import Payment, PaymentEvent
from apps.recovery.models import RecoveryAction, ResultChoices
from apps.recovery.services import process_failed_payment, record_recovery_outcome


SUCCESS_EVENTS = {'payment.captured', 'payment_link.paid', 'subscription.charged'}


def _event_id(request, payload):
    return request.headers.get('X-Razorpay-Event-Id') or payload.get('id') or hashlib.sha256(request.body).hexdigest()


def _payment_entity(payload):
    envelope = payload.get('payload', {})
    for key in ('payment', 'payment_link'):
        entity = envelope.get(key, {}).get('entity', {})
        if entity:
            return entity
    return {}


def _process_event(event):
    entity = _payment_entity(event.payload)
    if event.event_type == 'payment.failed':
        process_failed_payment(entity)
        return
    if event.event_type not in SUCCESS_EVENTS:
        return

    payment_id = entity.get('id') or entity.get('payment_id')
    action_id = entity.get('reference_id')
    action = None
    if action_id:
        action = RecoveryAction.objects.filter(id=action_id).select_related('recovery_case__payment').first()
    if action is None and payment_id:
        payment = Payment.objects.filter(razorpay_payment_id=payment_id).first()
        case = getattr(payment, 'recovery_case', None) if payment else None
        if case:
            action = case.recovery_actions.filter(execution_status='EXECUTED').order_by('-created_at').first()
    if action:
        amount = entity.get('amount') or action.recovery_case.payment.amount_paise
        record_recovery_outcome(action, ResultChoices.RECOVERED, amount, source=f'RAZORPAY:{event.event_type}')


@csrf_exempt
def razorpay_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    signature = request.headers.get('X-Razorpay-Signature')
    if not signature:
        return JsonResponse({'error': 'Missing signature'}, status=400)
    secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    expected = hmac.new(secret.encode('utf-8'), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event_id = _event_id(request, payload)
    with transaction.atomic():
        event, created = PaymentEvent.objects.get_or_create(
            event_id=event_id,
            defaults={'event_type': payload.get('event', ''), 'payload': payload},
        )
        if not created:
            return JsonResponse({'status': 'duplicate'})
        try:
            _process_event(event)
        except Exception as exc:
            event.status = PaymentEvent.FAILED
            event.error_message = str(exc)
            event.processed_at = timezone.now()
            event.save(update_fields=['status', 'error_message', 'processed_at'])
            return JsonResponse({'error': 'Event processing failed'}, status=500)
        event.status = PaymentEvent.PROCESSED
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'processed_at'])
    return JsonResponse({'status': 'ok'})
