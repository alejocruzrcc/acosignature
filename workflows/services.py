from django.utils import timezone

from accounts.models import User
from documents.models import Document, DocumentSignatory

from .models import AuditEvent


class WorkflowService:
    @staticmethod
    def _display_name(user):
        full = (user.get_full_name() or '').strip()
        return full or user.username

    @staticmethod
    def _log_event(action, actor=None, document=None, ip_address=None, metadata=None):
        AuditEvent.objects.create(
            action=action,
            actor=actor,
            document=document,
            ip_address=ip_address,
            metadata=metadata or {},
        )

    @staticmethod
    def sign_document(document: Document, actor: User, ip_address=None):
        if actor.role not in {User.Roles.ADMIN, User.Roles.REVIEWER, User.Roles.CLIENT}:
            raise ValueError('Rol sin permisos para firmar.')
        if document.status in {Document.Status.APPROVED, Document.Status.REJECTED}:
            raise ValueError('Documento en estado final, no se puede firmar.')

        signatories = list(document.signatories.all())
        if signatories:
            current_pending = (
                DocumentSignatory.objects.filter(document=document, status=DocumentSignatory.Status.PENDING)
                .select_related('user')
                .order_by('sign_order', 'id')
                .first()
            )
            if not document.signatories.filter(user=actor).exists():
                raise ValueError('No eres firmante asignado para este documento.')
            if not current_pending:
                raise ValueError('No hay firmantes pendientes para este documento.')
            if current_pending.user_id != actor.id:
                pending_name = WorkflowService._display_name(current_pending.user)
                raise ValueError(f'Aún no es tu turno de firma. Pendiente por: {pending_name}.')

            updated = DocumentSignatory.objects.filter(pk=current_pending.pk).update(status=DocumentSignatory.Status.SIGNED)
            if updated == 0:
                raise ValueError('No se pudo registrar la firma en el turno esperado.')

            rejected = DocumentSignatory.objects.filter(document=document, status=DocumentSignatory.Status.REJECTED).exists()
            pending = DocumentSignatory.objects.filter(document=document, status=DocumentSignatory.Status.PENDING).exists()
            if rejected:
                new_status = Document.Status.REJECTED
            elif pending:
                new_status = Document.Status.PENDING
            else:
                new_status = Document.Status.APPROVED
            if document.status != new_status:
                document.status = new_status
                document.save(update_fields=['status', 'updated_at'])

            WorkflowService._log_event(
                action=AuditEvent.Actions.SIGN,
                actor=actor,
                document=document,
                ip_address=ip_address,
                metadata={'new_status': document.status, 'multi_signatory': True},
            )
            return

        document.status = Document.Status.SIGNED
        document.save(update_fields=['status', 'updated_at'])
        WorkflowService._log_event(
            action=AuditEvent.Actions.SIGN,
            actor=actor,
            document=document,
            ip_address=ip_address,
            metadata={'new_status': Document.Status.SIGNED, 'multi_signatory': False},
        )

    @staticmethod
    def approve_document(document: Document, actor: User, ip_address=None):
        if actor.role not in {User.Roles.ADMIN, User.Roles.REVIEWER}:
            raise ValueError('Rol sin permisos para aprobar.')
        document.status = Document.Status.APPROVED
        document.save(update_fields=['status', 'updated_at'])
        WorkflowService._log_event(
            action=AuditEvent.Actions.APPROVE,
            actor=actor,
            document=document,
            ip_address=ip_address,
            metadata={'new_status': Document.Status.APPROVED},
        )

    @staticmethod
    def reject_document(document: Document, actor: User, ip_address=None):
        if actor.role not in {User.Roles.ADMIN, User.Roles.REVIEWER}:
            raise ValueError('Rol sin permisos para rechazar.')
        document.status = Document.Status.REJECTED
        document.save(update_fields=['status', 'updated_at'])
        WorkflowService._log_event(
            action=AuditEvent.Actions.REJECT,
            actor=actor,
            document=document,
            ip_address=ip_address,
            metadata={'new_status': Document.Status.REJECTED},
        )

    @staticmethod
    def reject_by_signatory(document: Document, actor: User, reason: str, ip_address=None):
        if document.status in {Document.Status.APPROVED, Document.Status.REJECTED}:
            raise ValueError('Documento en estado final, no se puede rechazar.')

        signatory = DocumentSignatory.objects.filter(document=document, user=actor).first()
        if not signatory:
            raise ValueError('No eres firmante asignado para este documento.')
        if signatory.status == DocumentSignatory.Status.SIGNED:
            raise ValueError('Ya firmaste este documento, no puedes rechazarlo.')
        if signatory.status == DocumentSignatory.Status.REJECTED:
            raise ValueError('Ya rechazaste este documento.')
        current_pending = (
            DocumentSignatory.objects.filter(document=document, status=DocumentSignatory.Status.PENDING)
            .select_related('user')
            .order_by('sign_order', 'id')
            .first()
        )
        if not current_pending:
            raise ValueError('No hay firmantes pendientes para este documento.')
        if current_pending.user_id != actor.id:
            pending_name = WorkflowService._display_name(current_pending.user)
            raise ValueError(f'Aún no es tu turno de firma. Pendiente por: {pending_name}.')

        signatory.status = DocumentSignatory.Status.REJECTED
        signatory.rejection_reason = reason.strip()
        signatory.rejected_at = timezone.now()
        signatory.save(update_fields=['status', 'rejection_reason', 'rejected_at', 'updated_at'])

        document.status = Document.Status.REJECTED
        document.save(update_fields=['status', 'updated_at'])

        WorkflowService._log_event(
            action=AuditEvent.Actions.REJECT,
            actor=actor,
            document=document,
            ip_address=ip_address,
            metadata={'new_status': Document.Status.REJECTED, 'reason': reason[:500]},
        )
