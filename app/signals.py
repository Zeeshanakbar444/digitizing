from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from .models import *

def _norm(value):
    return (str(value).strip().lower() if value is not None else None)

def setup_order_signals(model_class, email_template_name, site_url, main_subject, type):
    # 1) Capture the previous status BEFORE saving
    @receiver(pre_save, sender=model_class)
    def _cache_old_status(sender, instance, **kwargs):
        if instance.pk:
            try:
                instance._old_status = sender.objects.only('order_status').get(pk=instance.pk).order_status
            except sender.DoesNotExist:
                instance._old_status = None
        else:
            instance._old_status = None

    # 2) Decide and send after save (and after commit)
    @receiver(post_save, sender=model_class)
    def _send_order_delivered_email(sender, instance, created=False, **kwargs):
        old_status = getattr(instance, '_old_status', None)
        new_status = getattr(instance, 'order_status', None)

        old_n = _norm(old_status)
        new_n = _norm(new_status)

        # print(f"Old status: {old_status} ({old_n}); New status: {new_status} ({new_n})")

        # Must be delivered now
        if new_n != 'delivered':
            # print("Order is not delivered. Email not sent.")
            return

        # Skip duplicates if it was already delivered
        if old_n == 'delivered':
            # print("Already delivered before. Skipping duplicate email.")
            return

        # Basic amount check
        if not getattr(instance, 'amount', None) or instance.amount <= 0:
            # print("Amount not available. Email not sent.")
            return

        # Edited vs normal
        is_edited = (old_n == 'edited')

        def send_email_with_attachments():
            # Pick an ID to show
            if "Order" in main_subject:
                order_or_estimate_id = getattr(instance, 'order_id', getattr(instance, 'id', None))
            else:
                order_or_estimate_id = getattr(instance, 'estimate_id', getattr(instance, 'id', None))

            # Subject line varies if edited
            subject = (
                f"Your edited {type} {main_subject} Delivered ({order_or_estimate_id}) {instance.design_name} Logo"
                if is_edited else
                f"Your {type} {main_subject} Delivered ({order_or_estimate_id}) {instance.design_name} Logo"
            )

            to_email = instance.user.email

            context = {
                'user': instance.user,
                'order': instance,
                'site_url': site_url,
                'is_edited': is_edited,   # used by the template wording
            }

            message = render_to_string(email_template_name, context)

            email = EmailMessage(
                subject,
                message,
                to=[to_email],
                cc=['info@highfivedigitizing.com']
            )
            email.content_subtype = 'html'

            # print("Prepared email")

            # Attach visible files safely
            # Assumes a related_name='files' and fields is_visible, file
            for file_obj in getattr(instance, 'files', []).filter(is_visible=True):
                if file_obj.file:
                    filename = file_obj.file.name.split('/')[-1]
                    try:
                        with file_obj.file.open('rb') as f:
                            email.attach(
                                filename,
                                f.read(),
                                getattr(file_obj.file, 'content_type', 'application/octet-stream')
                            )
                    except Exception as e:
                        print(f"Error attaching file {filename}: {e}")

            email.send()
            # print("Email sent")

        transaction.on_commit(send_email_with_attachments)

def setup_order_created_signal(model_class, email_template_name, site_url, main_subject, type):
    """
    Sets up signals so that when an order is created (from frontend or admin),
    a confirmation email with all artworks is sent once everything is saved.
    """

    @receiver(post_save, sender=model_class)
    def _send_order_created_email(sender, instance, created=False, **kwargs):
        if not created:
            return  # only on first creation

        def send_email_with_attachments():
            # Ensure we don't send if no artworks exist yet
            if not hasattr(instance, "artworks") or instance.artworks.count() == 0:
                return

            order_or_estimate_id = getattr(instance, 'order_id', getattr(instance, 'id', None))

            subject = f"Your {type} {main_subject} Received ({order_or_estimate_id}) {instance.design_name} Logo"
            to_email = instance.user.email

            context = {
                'user': instance.user,
                'order': instance,
                'site_url': site_url,
            }

            message = render_to_string(email_template_name, context)

            email = EmailMessage(
                subject,
                message,
                to=[to_email],
                cc=['info@highfivedigitizing.com']
            )
            email.content_subtype = 'html'

            # Attach all artworks
            for artwork in instance.artworks.all():
                if artwork.file:
                    filename = artwork.file.name.split('/')[-1]
                    try:
                        with artwork.file.open('rb') as f:
                            email.attach(
                                filename,
                                f.read(),
                                getattr(artwork.file, 'content_type', 'application/octet-stream')
                            )
                    except Exception as e:
                        print(f"Error attaching file {filename}: {e}")

            email.send()

        # Delay until transaction commits (so artworks are saved too)
        transaction.on_commit(send_email_with_attachments)


setup_order_created_signal(
    DigitizingOrder,
    email_template_name='app/emails/order_placed_email.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Order',
    type='Digitizing',
)

setup_order_created_signal(
    VectorOrder,
    email_template_name='app/emails/order_placed_email.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Order',
    type='Vector',
)

setup_order_created_signal(
    PatchesOrder,
    email_template_name='app/emails/order_placed_email.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Order',
    type='Patch',
)

setup_order_signals(
    DigitizingOrder,
    email_template_name='app/emails/order_completed.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Order',
    type='Digitizing',
)

setup_order_signals(
    VectorOrder,
    email_template_name='app/emails/order_completed.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Order',
    type='Vector',
)

setup_order_signals(
    PatchesOrder,
    email_template_name='app/emails/order_completed.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Order',
    type='Patch',
)

setup_order_signals(
    DigitizingEstimate,
    email_template_name='app/emails/estimate_completed.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Quote',
    type='Digitizing',
)

setup_order_signals(
    VectorEstimate,
    email_template_name='app/emails/estimate_completed.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Quote',
    type='Vector',
)

setup_order_signals(
    PatchesEstimates,
    email_template_name='app/emails/estimate_completed.html',
    site_url='https://portal.highfivedigitizing.com/',
    main_subject='Quote',
    type='Patch',
)