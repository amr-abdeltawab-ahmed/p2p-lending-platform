#!/usr/bin/env python
"""
Database setup script for P2P Lending Platform
Run this to create migrations and set up the database manually if needed.
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'p2p_lending_platform.settings')
    django.setup()

    print("🔄 Setting up database...")

    # Create migrations for each app
    apps = ['users', 'wallets', 'loans', 'common']
    for app in apps:
        print(f"📝 Creating migrations for {app}...")
        try:
            execute_from_command_line(['manage.py', 'makemigrations', app])
        except Exception as e:
            print(f"⚠️  Warning: Could not create migrations for {app}: {e}")

    # Create any remaining migrations
    print("📝 Creating remaining migrations...")
    execute_from_command_line(['manage.py', 'makemigrations'])

    # Apply migrations
    print("🗄️  Applying migrations...")
    execute_from_command_line(['manage.py', 'migrate'])

    # Seed database
    print("🌱 Seeding database...")
    try:
        execute_from_command_line(['manage.py', 'seed_data', '--with-loan'])
    except Exception as e:
        print(f"⚠️  Warning: Could not seed database: {e}")

    print("✅ Database setup complete!")
