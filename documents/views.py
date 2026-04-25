from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsReviewerOrAdmin
from workflows.services import WorkflowService

from .filters import DocumentFilter
from .models import Document
from .serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = DocumentFilter
    queryset = Document.objects.select_related('uploaded_by').all()
    throttle_scope = 'documents'

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().filter(archived_at__isnull=True)
        if user.role in {User.Roles.ADMIN, User.Roles.REVIEWER}:
            return qs
        return qs.filter(signatories__user=user).distinct()

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user, status=Document.Status.PENDING)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.role == User.Roles.CLIENT and instance.uploaded_by_id != request.user.id:
            return Response({'detail': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.role == User.Roles.CLIENT and instance.uploaded_by_id != request.user.id:
            return Response({'detail': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @staticmethod
    def _get_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @action(methods=['post'], detail=True, permission_classes=[IsAuthenticated, IsReviewerOrAdmin])
    def approve(self, request, pk=None):
        doc = self.get_object()
        try:
            WorkflowService.approve_document(doc, request.user, ip_address=self._get_ip(request))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(doc).data)

    @action(methods=['post'], detail=True, permission_classes=[IsAuthenticated, IsReviewerOrAdmin])
    def reject(self, request, pk=None):
        doc = self.get_object()
        try:
            WorkflowService.reject_document(doc, request.user, ip_address=self._get_ip(request))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(doc).data)
