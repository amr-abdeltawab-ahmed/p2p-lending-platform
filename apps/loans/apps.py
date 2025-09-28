from django.apps import AppConfig


class LoansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.loans'

    def ready(self):
        """Import signals when Django starts."""
        import apps.loans.signals