"""
Users API Views - Function-based views for DRF compatibility
Converted from controller pattern to proper DRF function-based views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.common.throttling import AuthOperationsThrottle
from apps.common.serializers import ErrorResponseSerializer, ValidationErrorResponseSerializer, TokenResponseSerializer
from .serializers import UserSerializer, LoginSerializer
from .services import UserService

# Initialize service once
user_service = UserService()

@extend_schema(
    request=UserSerializer,
    responses={
        201: UserSerializer,
        400: ValidationErrorResponseSerializer
    },
    summary="Register a new user",
    description="Create a new user account for borrower or lender"
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthOperationsThrottle])
def register(request):
    """Register a new user (borrower or lender)"""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = user_service.register_user(serializer.validated_data)
        user_serializer = UserSerializer(user)
        return Response(user_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=LoginSerializer,
    responses={
        200: TokenResponseSerializer,
        401: ErrorResponseSerializer,
        400: ValidationErrorResponseSerializer
    },
    summary="User login",
    description="Authenticate user and return access token"
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthOperationsThrottle])
def login(request):
    """Authenticate user and return token"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        auth_data = user_service.authenticate_user(
            serializer.validated_data['username'],
            serializer.validated_data['password']
        )
        if auth_data:
            user_serializer = UserSerializer(auth_data['user'])
            return Response({
                'token': auth_data['token'],
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    responses={
        200: UserSerializer,
        404: ErrorResponseSerializer
    },
    summary="Get user profile",
    description="Retrieve authenticated user's profile information"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get authenticated user's profile"""
    user = user_service.get_user_profile(request.user.id)
    if user:
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    request=UserSerializer,
    responses={
        200: UserSerializer,
        400: ValidationErrorResponseSerializer,
        404: ErrorResponseSerializer
    },
    summary="Update user profile",
    description="Update authenticated user's profile information"
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update authenticated user's profile"""
    serializer = UserSerializer(data=request.data, partial=True)
    if serializer.is_valid():
        user_data = serializer.validated_data.copy()
        profile_data = user_data.pop('profile', {})

        user = user_service.update_user_profile(
            request.user.id,
            user_data,
            profile_data
        )
        if user:
            user_serializer = UserSerializer(user)
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)