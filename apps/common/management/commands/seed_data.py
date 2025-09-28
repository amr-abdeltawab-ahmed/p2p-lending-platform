import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from apps.wallets.models import Wallet
from apps.loans.models import Loan
from apps.users.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with test data for P2P lending platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-loan',
            action='store_true',
            help='Also create a sample loan request',
        )
        parser.add_argument(
            '--environment',
            type=str,
            choices=['development', 'testing', 'staging'],
            default='development',
            help='Target environment for seeding (prevents accidental production seeding)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force seeding even if not in development mode',
        )

    def handle(self, *args, **options):
        # Safety check: prevent accidental production seeding
        environment = os.environ.get('DJANGO_ENVIRONMENT', 'development')
        if environment == 'production' and not options['force']:
            self.stdout.write(
                self.style.ERROR('❌ Cannot seed production database without --force flag')
            )
            return

        if settings.DEBUG is False and not options['force']:
            self.stdout.write(
                self.style.ERROR('❌ Cannot seed when DEBUG=False without --force flag')
            )
            return

        self.stdout.write(self.style.SUCCESS('Starting database seeding...'))
        self.stdout.write(f'Environment: {environment}')
        self.stdout.write(f'Debug mode: {settings.DEBUG}')

        with transaction.atomic():
            # Create admin superuser
            admin = self.create_admin()

            # Create borrower
            borrower = self.create_borrower()

            # Create lender
            lender = self.create_lender()

            # Optionally create loan request
            loan = None
            if options['with_loan']:
                loan = self.create_sample_loan(borrower)

        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))
        self.stdout.write(self.style.WARNING('\nTest Login Credentials:'))
        self.stdout.write(f'Admin - Username: admin, Password: admin123')
        self.stdout.write(f'Borrower - Username: john_borrower, Password: testpass123')
        self.stdout.write(f'Lender - Username: sarah_lender, Password: testpass123')

        if loan:
            self.stdout.write(self.style.WARNING(f'\nSample loan created with ID: {loan.id}'))

    def create_admin(self):
        """Create an admin superuser for testing"""
        username = 'admin'

        # Check if admin already exists (idempotent)
        admin, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )

        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(f'✓ Created admin superuser: {admin.username} ({admin.email})')
        else:
            # Ensure existing admin has proper permissions
            if not admin.is_superuser or not admin.is_staff:
                admin.is_superuser = True
                admin.is_staff = True
                admin.save()
                self.stdout.write(f'✓ Updated admin permissions: {admin.username}')
            else:
                self.stdout.write(f'✓ Admin superuser already exists: {admin.username}')

        return admin

    def create_borrower(self):
        """Create a borrower user with realistic attributes"""
        username = 'john_borrower'

        # Check if borrower already exists (idempotent)
        borrower, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': 'john.doe@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'BORROWER'
            }
        )

        if created:
            borrower.set_password('testpass123')
            borrower.save()
            self.stdout.write(f'✓ Created borrower: {borrower.username} ({borrower.email})')
        else:
            self.stdout.write(f'✓ Borrower already exists: {borrower.username}')

        # Create or get borrower profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=borrower,
            defaults={
                'phone_number': '+1234567890',
                'date_of_birth': '1990-05-15',
                'address': '123 Main Street, Anytown, USA'
            }
        )

        if profile_created:
            self.stdout.write(f'  → Created borrower profile with phone: {profile.phone_number}')
        else:
            self.stdout.write(f'  → Borrower profile already exists')

        # Create or get wallet for borrower
        wallet, wallet_created = Wallet.objects.get_or_create(
            user=borrower,
            defaults={'balance': Decimal('1000.00')}  # Small initial balance
        )

        if wallet_created:
            self.stdout.write(f'  → Created wallet with balance: ${wallet.balance}')
        else:
            self.stdout.write(f'  → Wallet exists with balance: ${wallet.balance}')

        return borrower

    def create_lender(self):
        """Create a lender user with sufficient balance for loan + fee"""
        username = 'sarah_lender'

        # Check if lender already exists (idempotent)
        lender, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': 'sarah.smith@example.com',
                'first_name': 'Sarah',
                'last_name': 'Smith',
                'role': 'LENDER'
            }
        )

        if created:
            lender.set_password('testpass123')
            lender.save()
            self.stdout.write(f'✓ Created lender: {lender.username} ({lender.email})')
        else:
            self.stdout.write(f'✓ Lender already exists: {lender.username}')

        # Create or get lender profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=lender,
            defaults={
                'phone_number': '+1987654321',
                'date_of_birth': '1985-08-22',
                'address': '456 Oak Avenue, Investment City, USA'
            }
        )

        if profile_created:
            self.stdout.write(f'  → Created lender profile with phone: {profile.phone_number}')
        else:
            self.stdout.write(f'  → Lender profile already exists')

        # Create or get wallet for lender with sufficient balance
        required_balance = Decimal('5003.75')  # $5000 loan + $3.75 fee
        wallet, wallet_created = Wallet.objects.get_or_create(
            user=lender,
            defaults={'balance': Decimal('10000.00')}  # More than enough for multiple loans
        )

        if wallet_created:
            self.stdout.write(f'  → Created wallet with balance: ${wallet.balance}')
        else:
            # Ensure existing wallet has sufficient balance
            if wallet.balance < required_balance:
                wallet.balance = Decimal('10000.00')
                wallet.save()
                self.stdout.write(f'  → Updated wallet balance to: ${wallet.balance}')
            else:
                self.stdout.write(f'  → Wallet exists with balance: ${wallet.balance}')

        self.stdout.write(f'  → Sufficient for $5000 loan + $3.75 fee = $5003.75 ✓')

        return lender

    def create_sample_loan(self, borrower):
        """Create a sample loan request for testing"""
        # Check if loan already exists for this borrower (idempotent)
        loan, created = Loan.objects.get_or_create(
            borrower=borrower,
            amount=Decimal('5000.00'),
            defaults={
                'term_months': 6,
                'annual_interest_rate': Decimal('15.00'),
                'purpose': 'Business expansion and inventory purchase',
                'status': 'REQUESTED'
            }
        )

        if created:
            self.stdout.write(f'✓ Created sample loan request:')
            self.stdout.write(f'  → Loan ID: {loan.id}')
            self.stdout.write(f'  → Amount: ${loan.amount}')
            self.stdout.write(f'  → Term: {loan.term_months} months')
            self.stdout.write(f'  → Interest Rate: {loan.annual_interest_rate}%')
            self.stdout.write(f'  → Status: {loan.status}')
            self.stdout.write(f'  → Purpose: {loan.purpose}')
        else:
            self.stdout.write(f'✓ Sample loan already exists: ID {loan.id}')

        return loan