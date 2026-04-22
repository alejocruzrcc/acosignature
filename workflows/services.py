from accounts.models import User
from documents.models import Document, DocumentSignatory

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

        signatories = list(document.signatories.all())
        if signatories:
            updated = DocumentSignatory.objects.filter(document=document, user=actor, status=DocumentSignatory.Status.PENDING).update(
                status=DocumentSignatory.Status.SIGNED
            )
            if updated == 0 and not document.signatories.filter(user=actor).exists():
                raise ValueError('No eres firmante asignado para este documento.')

            pending = DocumentSignatory.objects.filter(document=document, status=DocumentSignatory.Status.PENDING).exists()
            new_status = Document.Status.PENDING if pending else Document.Status.APPROVED
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
