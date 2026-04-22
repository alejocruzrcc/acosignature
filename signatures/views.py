from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.models import User

from .models import Signature
from .serializers import SignatureSerializer


class SignDocumentView(generics.CreateAPIView):
    serializer_class = SignatureSerializer
    permission_classes = [IsAuthenticated]


class DocumentSignatureListView(generics.ListAPIView):
    serializer_class = SignatureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        document_id = self.kwargs['id']
        user = self.request.user
        qs = Signature.objects.select_related('document', 'user').filter(document_id=document_id)
        if user.role in {User.Roles.ADMIN, User.Roles.REVIEWER}:
            return qs
        return qs.filter(user=user)
