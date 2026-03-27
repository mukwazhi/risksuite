from django.core.management.base import BaseCommand
import logging


class Command(BaseCommand):
    help = "Send a test server log to trigger email handlers"

    def handle(self, *args, **options):
        logger = logging.getLogger('riskregister.test')
        try:
            raise RuntimeError("Test exception for server log email")
        except Exception:
            logger.exception("Sending test server log (exception)")
        self.stdout.write(self.style.SUCCESS("Test log emitted"))
