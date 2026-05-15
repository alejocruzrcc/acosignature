"""Helpers para firmantes usando prefetch (evita N+1 en listados y detalle)."""

from __future__ import annotations

from typing import List, Optional

from django.db.models import Exists, OuterRef, Subquery

from documents.models import Document, DocumentSignatory


def signatories_list(document: Document) -> List[DocumentSignatory]:
    return list(document.signatories.all())


def signatory_for_user(document: Document, user) -> Optional[DocumentSignatory]:
    return next((s for s in signatories_list(document) if s.user_id == user.id), None)


def current_pending_signatory(document: Document) -> Optional[DocumentSignatory]:
    pending = [s for s in signatories_list(document) if s.status == DocumentSignatory.Status.PENDING]
    if not pending:
        return None
    return min(pending, key=lambda s: (s.sign_order, s.id))


def rejected_signatory(document: Document) -> Optional[DocumentSignatory]:
    rejected = [s for s in signatories_list(document) if s.status == DocumentSignatory.Status.REJECTED]
    if not rejected:
        return None
    return min(rejected, key=lambda s: (s.rejected_at or s.id, s.id))


def is_fully_signed(document: Document) -> bool:
    signatories = signatories_list(document)
    return bool(signatories) and all(s.status == DocumentSignatory.Status.SIGNED for s in signatories)


def user_can_access_document(user, document: Document) -> bool:
    if user.role in {user.Roles.ADMIN, user.Roles.REVIEWER}:
        return True
    prefetched = getattr(document, '_prefetched_objects_cache', None)
    if prefetched and 'signatories' in prefetched:
        return any(s.user_id == user.id for s in document.signatories.all())
    return DocumentSignatory.objects.filter(document_id=document.pk, user=user).exists()


def approval_list_queryset(user, *, category: str = '', query: str = ''):
    qs = (
        Document.objects.select_related('uploaded_by')
        .prefetch_related('signatories__user')
        .filter(archived_at__isnull=True)
    )
    if category:
        qs = qs.filter(category=category)
    if query:
        qs = qs.filter(title__icontains=query)
    if user.role == user.Roles.CLIENT:
        qs = qs.filter(
            Exists(
                DocumentSignatory.objects.filter(document_id=OuterRef('pk'), user=user)
            )
        )
    return qs.order_by('-created_at')


def queryset_pending_signature_for_user(user, *, category: str = '', query: str = ''):
    """Documentos en los que es el turno de firma del usuario."""
    turn_user = (
        DocumentSignatory.objects.filter(
            document_id=OuterRef('pk'),
            status=DocumentSignatory.Status.PENDING,
        )
        .order_by('sign_order', 'id')
        .values('user_id')[:1]
    )
    qs = approval_list_queryset(user, category=category, query=query).filter(
        status=Document.Status.PENDING,
    ).annotate(_turn_user_id=Subquery(turn_user)).filter(_turn_user_id=user.id)
    return qs


def document_detail_queryset():
    return Document.objects.select_related('uploaded_by').prefetch_related(
        'signatories__user',
        'signatures__user',
    )
