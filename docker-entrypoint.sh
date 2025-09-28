#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Django application..."

# Function to wait for database
wait_for_db() {
    echo "Waiting for database connection..."
    while ! python manage.py check --database default; do
        echo "Database unavailable - sleeping"
        sleep 1
    done
    echo "Database connection established!"
}

# Function to run migrations
run_migrations() {
    echo "Running database migrations..."
    python manage.py makemigrations --noinput
    python manage.py migrate --noinput
    echo "Migrations completed!"
}

# Function to collect static files
collect_static() {
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
    echo "Static files collected!"
}

# Function to create superuser if it doesn't exist
create_superuser() {
    if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
        echo "Creating superuser..."
        python manage.py createsuperuser \
            --noinput \
            --username $DJANGO_SUPERUSER_USERNAME \
            --email $DJANGO_SUPERUSER_EMAIL \
            2>/dev/null || echo "Superuser already exists or creation failed"
        echo "Superuser creation completed!"
    else
        echo "Superuser environment variables not set. Skipping superuser creation."
    fi
}

# Main execution
main() {
    # Wait for database to be ready
    wait_for_db

    # Run migrations
    run_migrations

    # Collect static files (only in production)
    if [ "$DEBUG" = "False" ] || [ "$DEBUG" = "false" ]; then
        collect_static
    fi

    # Create superuser if environment variables are provided
    create_superuser

    # Execute the command passed to the script
    echo "Starting application with command: $@"
    exec "$@"
}

# Run main function with all arguments
main "$@"