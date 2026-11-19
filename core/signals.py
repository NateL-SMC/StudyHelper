from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """Every new user gets a Profile. Superusers (createsuperuser) become admins."""
    if created:
        Profile.objects.create(
            user=instance,
            role=Profile.ROLE_ADMIN if instance.is_superuser else Profile.ROLE_STUDENT,
            city=settings.DEFAULT_CITY,
        )
