# P2P Lending Platform

Django REST Framework platform with layered architecture (Controller → Service → Repository).

## Quick Start

```bash
git clone <repository-url>
cd p2p-lending-platform
cp .env.example .env

# Make sure Docker Desktop is running, then:
cd docker
docker-compose up --build
```

**Access**: http://localhost:8000 (API Root with endpoint information)

**⚠️ Troubleshooting**: If you get Docker connection errors:
1. Ensure Docker Desktop is running
2. Try: `docker --version` to verify Docker is accessible
3. On Windows, restart Docker Desktop if needed

## Configuration

### Environment Variables (.env)
```bash
# Core
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@db:5432/p2p_lending
REDIS_URL=redis://redis:6379/0

# Platform
PLATFORM_FEE=3.75
DEFAULT_PAYMENT_TERMS=6

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# Rate Limiting
THROTTLE_RATE=10/min
```

### Docker Commands
```bash
cd docker
docker-compose -p p2p_lending_platform up --build          # Start services
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose logs -f web         # View logs
docker-compose down                # Stop services
```

## API Documentation

**Swagger UI**: http://localhost:8000/api/swagger/
**Admin Panel**: http://localhost:8000/admin/

### Core Models

- **User**: Borrower/Lender with role-based permissions
- **Loan**: Amount, term, interest rate, status tracking
- **Offer**: Lender offers on loan requests
- **Payment**: Monthly payment schedule and tracking
- **Wallet**: User balance management
- **Transaction**: Complete financial history

### Quick Start with Test Data

**Option 1: Use Seeded Test Accounts**
```bash
# Seed database with test users and sample loan
docker-compose exec web python manage.py seed_data --with-loan

# Test accounts created:
# Admin: admin / admin123 (Superuser access)
# Borrower: john_borrower / testpass123 (Balance: $1,000)
# Lender: sarah_lender / testpass123 (Balance: $10,000)
```

**Option 2: Manual Registration**
```
1. POST /api/users/register/     → Create user account
2. POST /api/users/login/        → Get authentication token
3. POST /api/loans/              → Borrower creates loan request
4. GET  /api/loans/available/    → Lender views available loans
5. POST /api/loans/{id}/offer/   → Lender makes offer
6. POST /api/loans/{id}/accept-offer/ → Borrower accepts offer
7. POST /api/loans/{id}/fund/    → Lender funds loan
8. POST /api/loans/{id}/pay/     → Borrower makes payments
```

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/register/` | User registration |
| POST | `/api/users/login/` | Login (returns token) |
| GET | `/api/users/profile/` | Get user profile |

### Wallet Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/wallets/` | Get wallet details |
| POST | `/api/wallets/deposit/` | Deposit funds |
| POST | `/api/wallets/withdraw/` | Withdraw funds |
| GET | `/api/wallets/transactions/` | Transaction history |

### Loan Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/loans/` | Create loan (BORROWER) |
| GET | `/api/loans/available/` | Available loans (LENDER) |
| GET | `/api/loans/my-loans/` | User's loans |
| POST | `/api/loans/{id}/offer/` | Make offer (LENDER) |
| POST | `/api/loans/{id}/accept-offer/` | Accept offer (BORROWER) |
| POST | `/api/loans/{id}/fund/` | Fund loan (LENDER) |
| POST | `/api/loans/{id}/pay/` | Make payment (BORROWER) |
| GET | `/api/loans/{id}/schedule/` | Payment schedule |

## Loan States

- **REQUESTED** → Awaiting offers
- **PENDING_FUNDING** → Offer accepted, awaiting funding
- **FUNDED** → Active loan with payment schedule
- **COMPLETED** → All payments made

## Features

- **Redis Caching**: Intelligent caching of available loans with automatic invalidation
- **Celery + Beat**: Hourly background tasks for overdue payment management
- **Daily log rotation** (7-day retention)
- **API rate limiting** and throttling
- **Custom exception handling** with detailed error responses
- **Token-based authentication** with role-based permissions (BORROWER/LENDER)
- **Atomic financial transactions** with comprehensive audit trail

## Architecture

```
Views → Services → Repositories → Database
```

- **Views**: Handle HTTP requests, validation
- **Services**: Business logic, loan lifecycle
- **Repositories**: Database operations
- **Models**: Data structure and relationships

## Development

```bash
# Add migrations
docker-compose exec web python manage.py makemigrations

# Seed test data
docker-compose exec web python manage.py seed_data
docker-compose exec web python manage.py seed_data --with-loan

# Django shell
docker-compose exec web python manage.py shell

# View logs
docker-compose exec web tail -f logs/app.log
```

## Testing

The project includes comprehensive unit tests for all apps and integration tests for API endpoints.

### Running Unit Tests

**Using Django Test Runner (Recommended):**
```bash
# Run all tests
docker-compose exec web python manage.py test

# Run tests for specific app
docker-compose exec web python manage.py test apps.users
docker-compose exec web python manage.py test apps.wallets
docker-compose exec web python manage.py test apps.loans

# Run tests with verbose output
docker-compose exec web python manage.py test --verbosity=2

# Run specific test class
docker-compose exec web python manage.py test apps.users.tests.UserAPITest

# Run specific test method
docker-compose exec web python manage.py test apps.users.tests.UserAPITest.test_user_registration

# Run tests with coverage (if installed)
docker-compose exec web python manage.py test --debug-mode --failfast
```

### Integration Tests

```bash
# Run integration tests using Django test runner (recommended)
docker-compose exec web python manage.py test test_integration

# Or run as standalone script
docker-compose exec web python test_integration.py

# Test Swagger API endpoints
docker-compose exec web python test_swagger_endpoints.py

# Run cache and Celery tests
docker-compose exec web python test_cache_and_celery.py
```

### Local Development Testing

If running outside Docker:
```bash
# Install dependencies first
pip install -r requirements.txt

# Set environment
export DJANGO_SETTINGS_MODULE=p2p_lending_platform.settings

# Run tests
python manage.py test
python manage.py test test_integration
pytest
```

### Test Coverage

Each app includes:
- **Model Tests**: Database operations, validation, relationships
- **API Tests**: Authentication, CRUD operations, permissions
- **Service Tests**: Business logic, loan lifecycle, transactions
- **Repository Tests**: Data access patterns, query optimization

### Database Seeding

The project includes a `seed_data` management command to populate the database with test data:

```bash
# Seed users only
docker-compose exec web python manage.py seed_data

# Seed users + sample loan request
docker-compose exec web python manage.py seed_data --with-loan
```

**Test Accounts Created:**
- **Admin**: `admin` / `admin123` (Superuser access)
- **Borrower**: `john_borrower` / `testpass123` (Balance: $1,000)
- **Lender**: `sarah_lender` / `testpass123` (Balance: $10,000)

The lender has sufficient balance to fund a $5,000 loan + $3.75 platform fee.

## Redis Caching & Background Tasks

### **Redis Caching System**

The platform implements intelligent caching for optimal performance:

**What's Cached:**
- Available loans (loans without lenders, status = REQUESTED)
- Loan details and payment schedules
- User-specific loan lists
- Wallet information

**Automatic Cache Invalidation:**
- Triggered by Django signals when loans are created/updated
- Happens automatically on status changes (REQUESTED → PENDING_FUNDING → FUNDED)
- Ensures data consistency without manual intervention

**Manual Cache Management:**
```bash
# Clear all caches (Redis CLI)
docker-compose exec p2p_lending_redis redis-cli FLUSHALL

# Clear specific cache pattern (Django shell)
docker-compose exec p2p_lending_web python manage.py shell
>>> from apps.common.cache_utils import LoanCache
>>> LoanCache.invalidate_available_loans()
>>> LoanCache.invalidate_loan_detail(loan_id=123)
```

### **Celery Background Tasks**

The platform runs scheduled background tasks for automated loan management:

**Background Services:**
```bash
# Start all services (includes Celery worker & beat)
docker-compose up --build

# View Celery worker logs
docker-compose logs -f p2p_lending_celery_worker

# View Celery beat scheduler logs
docker-compose logs -f p2p_lending_celery_beat

# Run Celery commands manually
docker-compose exec p2p_lending_web celery -A p2p_lending_platform worker -l info
docker-compose exec p2p_lending_web celery -A p2p_lending_platform beat -l info
```

**Scheduled Tasks:**

| Task | Schedule | Purpose |
|------|----------|---------|
| `check_overdue_payments` | Every hour | Mark pending payments past due date as OVERDUE |
| `loan_status_summary_report` | Daily | Generate platform metrics and status summary |
| `cleanup_expired_loan_cache` | Weekly | Maintenance task for cache cleanup |

**Manual Task Execution:**
```bash
# Test overdue payment check
docker-compose exec p2p_lending_web python manage.py shell
>>> from apps.loans.tasks import check_overdue_payments
>>> result = check_overdue_payments.delay()
>>> print(result.get())

# Test loan status report
>>> from apps.loans.tasks import loan_status_summary_report
>>> result = loan_status_summary_report.delay()
>>> print(result.get())
```

**Task Monitoring:**
- All tasks log detailed results to `logs/app.log`
- Failed tasks are logged with error details
- Task results include timing and affected record counts