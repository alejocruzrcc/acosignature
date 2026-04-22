from accounts.models import User
from documents.models import Document

from .models import AuditEvent


class WorkflowService:
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
        if actor.role not in {User.Roles.ADMIN, User.Roles.CLIENT}:
            raise ValueError('Rol sin permisos para firmar.')
        if document.status in {Document.Status.APPROVED, Document.Status.REJECTED}:
            raise ValueError('Documento en estado final, no se puede firmar.')
        document.status = Document.Status.SIGNED
        document.save(update_fields=['status', 'updated_at'])
        WorkflowService._log_event(
            action=AuditEvent.Actions.SIGN,
            actor=actor,
            document=document,
            ip_address=ip_address,
            metadata={'new_status': Document.Status.SIGNED},
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
