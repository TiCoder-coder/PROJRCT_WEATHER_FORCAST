from .Base_login import BaseSerializerLogin
class LoginLoginCreate(BaseSerializerLogin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        required_fields = ["name", "userName", "password", "email", "role"]
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
