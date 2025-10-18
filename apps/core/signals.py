from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import UserProfile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create or update the user profile whenever the User model is saved.
    Handles duplicates gracefully to avoid conflicts.
    """
    try:
        if created:
            # For new users, use get_or_create to avoid duplicates
            profile, profile_created = UserProfile.objects.get_or_create(
                user=instance,
                defaults={'role': 'user', 'is_active': True}
            )
            if profile_created:
                print(f"✅ Created new profile for {instance.username}: {profile.id}")
            else:
                print(f"ℹ️  Profile already exists for {instance.username}: {profile.id}")
        else:
            # For existing users, get or create the profile
            profile, profile_created = UserProfile.objects.get_or_create(
                user=instance,
                defaults={'role': 'user', 'is_active': True}
            )
            if profile_created:
                print(f"✅ Created missing profile for existing user {instance.username}: {profile.id}")
            else:
                print(f"ℹ️  Updated profile for {instance.username}: {profile.id}")
    except IntegrityError as e:
        print(f"⚠️  Profile already exists for {instance.username}, skipping creation")
    except Exception as e:
        print(f"❌ Error in create_or_update_user_profile signal: {e}")
