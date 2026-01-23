from rest_framework import serializers
from Weather_Forcast_App.Models.Login import LoginModel
from bson import ObjectId
class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)
    
    def to_internal_value(self, data):
        try:
            return ObjectId(data)
        except Exception:
            raise serializers.ValidationError("Invalid ObjectId format")
class BaseSerializerLogin(serializers.ModelSerializer):
    class Meta:
        model = LoginModel
        fields = '__all__'