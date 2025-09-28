"""
Loans API Views - Function-based views for DRF compatibility
Converted from controller pattern to proper DRF function-based views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.common.throttling import FinancialOperationsThrottle, LoanCreationThrottle, OfferThrottle, PaymentThrottle
from apps.common.exceptions import (
    RolePermissionError, LoanNotFoundError, InsufficientFundsError,
    UnauthorizedLoanAccessError, InvalidLoanStateError
)
from apps.common.serializers import (
    ErrorResponseSerializer, ValidationErrorResponseSerializer, PaymentResponseSerializer
)
from .serializers import (
    LoanSerializer, CreateLoanSerializer, OfferSerializer,
    CreateOfferSerializer, AcceptOfferSerializer, PaymentSerializer
)
from .services import LoanService, OfferService, LoanFundingService, PaymentService

# Initialize services once
loan_service = LoanService()
offer_service = OfferService()
funding_service = LoanFundingService()
payment_service = PaymentService()

@extend_schema(
    request=CreateLoanSerializer,
    responses={
        201: LoanSerializer,
        400: ValidationErrorResponseSerializer,
        403: ErrorResponseSerializer
    },
    summary="Create a new loan request",
    description="Create a new loan request (borrowers only)"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([LoanCreationThrottle])
def create_loan(request):
    """Create a new loan request"""
    if request.user.role != 'BORROWER':
        raise RolePermissionError("Only borrowers can create loan requests")

    serializer = CreateLoanSerializer(data=request.data)
    if serializer.is_valid():
        try:
            loan = loan_service.create_loan(request.user, serializer.validated_data)
            response_serializer = LoanSerializer(loan)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    responses={200: LoanSerializer(many=True)},
    summary="Get available loans",
    description="Get all loans available for funding"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_loans(request):
    """Get all loans available for funding"""
    loans = loan_service.get_available_loans()
    serializer = LoanSerializer(loans, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    responses={
        200: LoanSerializer,
        404: ErrorResponseSerializer
    },
    summary="Get loan details",
    description="Get detailed information about a specific loan"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_detail(request, loan_id):
    """Get detailed information about a specific loan"""
    loan = loan_service.get_loan_details(loan_id)
    if not loan:
        return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = LoanSerializer(loan)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    responses={200: LoanSerializer(many=True)},
    summary="Get user's loans",
    description="Get all loans for the authenticated user"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_loans(request):
    """Get all loans for the authenticated user"""
    loans = loan_service.get_loans_by_user(request.user)
    serializer = LoanSerializer(loans, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    request=CreateOfferSerializer,
    responses={
        201: OfferSerializer,
        400: ValidationErrorResponseSerializer,
        403: ErrorResponseSerializer
    },
    summary="Create an offer for a loan",
    description="Create an interest rate offer for a loan (lenders only)"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([OfferThrottle])
def create_offer(request, loan_id):
    """Create an interest rate offer for a loan"""
    if request.user.role != 'LENDER':
        return Response({'error': 'Only lenders can make offers'},
                      status=status.HTTP_403_FORBIDDEN)

    serializer = CreateOfferSerializer(data=request.data)
    if serializer.is_valid():
        result = offer_service.create_offer(
            loan_id, request.user, serializer.validated_data['annual_interest_rate']
        )
        if result['success']:
            response_serializer = OfferSerializer(result['offer'])
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=AcceptOfferSerializer,
    responses={
        200: LoanSerializer,
        400: ValidationErrorResponseSerializer
    },
    summary="Accept an offer for a loan",
    description="Accept a lender's offer for a loan"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_offer(request, loan_id):
    """Accept a lender's offer for a loan"""
    serializer = AcceptOfferSerializer(data=request.data)
    if serializer.is_valid():
        result = offer_service.accept_offer(
            loan_id, serializer.validated_data['offer_id'], request.user
        )
        if result['success']:
            response_serializer = LoanSerializer(result['loan'])
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    responses={
        200: LoanSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer
    },
    summary="Fund a loan",
    description="Fund an accepted loan (lenders only)"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([FinancialOperationsThrottle])
def fund_loan(request, loan_id):
    """Fund an accepted loan"""
    if request.user.role != 'LENDER':
        return Response({'error': 'Only lenders can fund loans'},
                      status=status.HTTP_403_FORBIDDEN)

    try:
        result = funding_service.fund_loan(loan_id, request.user)
        if result['success']:
            response_serializer = LoanSerializer(result['loan'])
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    except InsufficientFundsError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except (LoanNotFoundError, UnauthorizedLoanAccessError, InvalidLoanStateError) as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    responses={
        200: PaymentResponseSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer
    },
    summary="Make a loan payment",
    description="Make a payment towards a loan (borrowers only)"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentThrottle])
def make_payment(request, loan_id):
    """Make a payment towards a loan"""
    if request.user.role != 'BORROWER':
        return Response({'error': 'Only borrowers can make loan payments'},
                      status=status.HTTP_403_FORBIDDEN)

    result = payment_service.make_payment(loan_id, request.user)
    if result['success']:
        response_data = {
            'message': 'Payment successful',
            'payment': PaymentSerializer(result['payment']).data
        }
        if result.get('loan_completed'):
            response_data['message'] += ' - Loan completed!'
        return Response(response_data, status=status.HTTP_200_OK)
    else:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    responses={200: PaymentSerializer(many=True)},
    summary="Get payment schedule",
    description="Get payment schedule for a loan"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_schedule(request, loan_id):
    """Get payment schedule for a loan"""
    payments = payment_service.get_payment_schedule(loan_id, request.user)
    serializer = PaymentSerializer(payments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    responses={
        200: PaymentSerializer(many=True),
        403: ErrorResponseSerializer
    },
    summary="Get pending payments",
    description="Get all pending payments for borrower"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_payments(request):
    """Get all pending payments for borrower"""
    if request.user.role != 'BORROWER':
        return Response({'error': 'Only borrowers can view pending payments'},
                      status=status.HTTP_403_FORBIDDEN)

    payments = payment_service.get_pending_payments(request.user)
    serializer = PaymentSerializer(payments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)