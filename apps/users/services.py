from typing import Optional, Dict, Any
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .repositories import UserRepository, UserProfileRepository
from .models import User


class UserService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.profile_repo = UserProfileRepository()

    def register_user(self, user_data: Dict[str, Any]) -> User:
        profile_data = user_data.pop('profile', {})

        user = self.user_repo.create_user(**user_data)

        if profile_data:
            self.profile_repo.create_profile(user=user, **profile_data)

        return user

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = authenticate(username=username, password=password)
        if user and user.is_active:
            token, created = Token.objects.get_or_create(user=user)
            return {
                'user': user,
                'token': token.key
            }
        return None

    def get_user_profile(self, user_id: int) -> Optional[User]:
        return self.user_repo.get_user_by_id(user_id)

    def update_user_profile(self, user_id: int, user_data: Dict[str, Any], profile_data: Dict[str, Any] = None) -> Optional[User]:
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return None

        if user_data:
            user = self.user_repo.update_user(user, **user_data)

        if profile_data:
            profile = self.profile_repo.get_profile_by_user(user)
            if profile:
                self.profile_repo.update_profile(profile, **profile_data)
            else:
                self.profile_repo.create_profile(user=user, **profile_data)

        return user

    def get_users_by_role(self, role: str) -> list:
        return self.user_repo.get_users_by_role(role)

    def delete_user(self, user_id: int) -> bool:
        user = self.user_repo.get_user_by_id(user_id)
        if user:
            return self.user_repo.delete_user(user)
        return False