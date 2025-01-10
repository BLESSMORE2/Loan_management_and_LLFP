from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from users.models import AuditTrail  # Import the AuditTrail model from the Users app

# Signal to log create and update actions
@receiver(post_save)
def log_create_or_update(sender, instance, created, **kwargs):
    if sender._meta.app_label == "users":  # Avoid logging changes to models in the Users app
        return

    action = "create" if created else "update"
    user = getattr(instance, "modified_by", None)  # Check if the model has a 'modified_by' field
    AuditTrail.objects.create(
        user=user,
        model_name=sender._meta.db_table,
        action=action,
        object_id=instance.pk,
        change_description=f"{action.title()}d object: {instance}",
    )

# Signal to log delete actions
@receiver(pre_delete)
def log_delete(sender, instance, **kwargs):
    if sender._meta.app_label == "users":  # Avoid logging changes to models in the Users app
        return

    user = getattr(instance, "modified_by", None)
    AuditTrail.objects.create(
        user=user,
        model_name=sender._meta.db_table,
        action="delete",
        object_id=instance.pk,
        change_description=f"Deleted object: {instance}",
    )
