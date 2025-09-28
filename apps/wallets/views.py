"""
Wallets API Views - Function-based views for DRF compatibility
Converted from controller pattern to proper DRF function-based views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.common.serializers import (
    ErrorResponseSerializer, ValidationErrorResponseSerializer,
    BalanceResponseSerializer, DepositResponseSerializer, WithdrawalResponseSerializer
)
from .serializers import WalletSerializer, DepositSerializer, WithdrawalSerializer, TransactionSerializer
from .services import WalletService

# Initialize service once
wallet_service = WalletService()

@extend_schema(
    responses={200: WalletSerializer},
    summary="Get user wallet",
    description="Get or create wallet for authenticated user"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet(request):
    """Get or create wallet for authenticated user"""
    wallet = wallet_service.get_or_create_wallet(request.user)
    serializer = WalletSerializer(wallet)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    request=DepositSerializer,
    responses={
        200: DepositResponseSerializer,
        400: ValidationErrorResponseSerializer
    },
    summary="Deposit funds",
    description="Deposit funds into user's wallet"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit(request):
    """Deposit funds into user's wallet"""
    serializer = DepositSerializer(data=request.data)
    if serializer.is_valid():
        result = wallet_service.deposit_funds(
            user=request.user,
            amount=serializer.validated_data['amount'],
            description=serializer.validated_data.get('description')
        )

        if result['success']:
            wallet = wallet_service.get_or_create_wallet(request.user)
            wallet_serializer = WalletSerializer(wallet)
            return Response({
                'message': 'Deposit successful',
                'wallet': wallet_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=WithdrawalSerializer,
    responses={
        200: WithdrawalResponseSerializer,
        400: ValidationErrorResponseSerializer
    },
    summary="Withdraw funds",
    description="Withdraw funds from user's wallet"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw(request):
    """Withdraw funds from user's wallet"""
    serializer = WithdrawalSerializer(data=request.data)
    if serializer.is_valid():
        result = wallet_service.withdraw_funds(
            user=request.user,
            amount=serializer.validated_data['amount'],
            description=serializer.validated_data.get('description')
        )

        if result['success']:
            wallet = wallet_service.get_or_create_wallet(request.user)
            wallet_serializer = WalletSerializer(wallet)
            return Response({
                'message': 'Withdrawal successful',
                'wallet': wallet_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    responses={200: TransactionSerializer(many=True)},
    summary="Get transaction history",
    description="Get transaction history for user's wallet"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_history(request):
    """Get transaction history for user's wallet"""
    limit = request.query_params.get('limit')
    limit = int(limit) if limit and limit.isdigit() else None

    transactions = wallet_service.get_transaction_history(request.user, limit)
    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    responses={200: BalanceResponseSerializer},
    summary="Get wallet balance",
    description="Get current wallet balance for user"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def balance(request):
    """Get current wallet balance for user"""
    balance = wallet_service.get_wallet_balance(request.user)
    return Response({'balance': balance}, status=status.HTTP_200_OK)