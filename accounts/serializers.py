from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'document_number',
            'phone', 'role', 'is_verified', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_verified')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'document_number', 'phone', 'role'
        )
        read_only_fields = ('id',)

    def validate_role(self, value):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return User.Roles.CLIENT
        if value in (User.Roles.ADMIN, User.Roles.REVIEWER) and request.user.role != User.Roles.ADMIN:
            raise serializers.ValidationError('Solo admin puede asignar admin/reviewer.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
