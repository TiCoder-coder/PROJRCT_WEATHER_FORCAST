from enum import Enum

class CustomEnum(Enum):
    @property
    def description(self):
        pass

# Dinh nghia class Role
class Role(CustomEnum):
    Guest = "Guest"
    Manager = "Manager"
    Admin = "Admin"