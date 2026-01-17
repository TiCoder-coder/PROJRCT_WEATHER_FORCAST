from django.core.management.base import BaseCommand
from decouple import config
from Weather_Forcast_App.scripts.Login_services import ManagerService

class SeedUser:
    role = "admin"

class Command(BaseCommand):
    help = "Seed admin account into MongoDB (first time)."

    def handle(self, *args, **options):
        username = config("USER_NAME_ADMIN", default=None)
        password = config("ADMIN_PASSWORD", default=None)
        email = config("ADMIN_EMAIL", default="admin@local.com")

        if not username or not password:
            self.stdout.write(self.style.ERROR("LACK USER_NAME_ADMIN OR ADMIN_PASSWORD in .env"))
            return

        try:
            seed_user = SeedUser()

            ManagerService.create_manager(
                seed_user,
                "Administrator",
                username,
                password,
                email,
                role="admin"
            )

            self.stdout.write(self.style.SUCCESS(f"Admin '{username}' created successfully in MongoDB!"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(str(e)))
