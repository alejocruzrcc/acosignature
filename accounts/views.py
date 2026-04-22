from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from workflows.models import AuditEvent

from .models import User
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    throttle_scope = 'auth'

    def get_permissions(self):
        if self.request.user.is_authenticated:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            serializer.save(role=User.Roles.CLIENT)
        else:
            serializer.save()


class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_scope = 'auth'

    @staticmethod
    def _get_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = User.objects.filter(username=request.data.get('username')).first()
            AuditEvent.objects.create(
                action=AuditEvent.Actions.LOGIN,
                actor=user,
                ip_address=self._get_ip(request),
                metadata={'success': True},
            )
        return response


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'auth'

    def get(self, request):
        return Response(UserSerializer(request.user).data)
