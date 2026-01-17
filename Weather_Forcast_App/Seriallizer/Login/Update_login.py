from .Base_login import BaseSerializerLogin

# Ham dung de tao ra du lieu json khi update cac thuoc tinh
class LoginUpdate(BaseSerializerLogin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False                                              # Cac thuoc tinh la khong bat buoc
        
        # Loai bo field id khi update
        if "id" in self.fields:
            self.fields.pop("id") 