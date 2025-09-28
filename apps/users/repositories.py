from typing import Optional, List
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


class UserRepository:
    @staticmethod
    def create_user(username: str, email: str, password: str, role: str, **kwargs) -> User:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            **kwargs
        )
        return user

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        try:
            return User.objects.select_related('profile').get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        try:
            return User.objects.select_related('profile').get(username=username)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_users_by_role(role: str) -> List[User]:
        return User.objects.filter(role=role).select_related('profile')

    @staticmethod
    def update_user(user: User, **kwargs) -> User:
        for field, value in kwargs.items():
            setattr(user, field, value)
        user.save()
        return user

    @staticmethod
    def delete_user(user: User) -> bool:
        try:
            user.delete()
            return True
        except Exception:
            return False


class UserProfileRepository:
    @staticmethod
    def create_profile(user: User, **kwargs) -> UserProfile:
        profile = UserProfile.objects.create(user=user, **kwargs)
        return profile

    @staticmethod
    def get_profile_by_user(user: User) -> Optional[UserProfile]:
        try:
            return UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return None

    @staticmethod
    def update_profile(profile: UserProfile, **kwargs) -> UserProfile:
        for field, value in kwargs.items():
            setattr(profile, field, value)
        profile.save()
        return profile