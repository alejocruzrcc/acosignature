from __future__ import annotations

import base64
import math
import mimetypes
from urllib.parse import quote, urlencode

from io import BytesIO

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from documents.models import Document, DocumentSignatory
from documents.services import build_signed_pdf_preview_bytes, rebuild_signed_pdf
from signatures.models import Signature
from workflows.services import WorkflowService

from .forms import DocumentCreateForm, DocumentEditForm, RejectionReasonForm, SignatureCaptureForm, UserProfileForm


def home(request):
    return render(request, 'portal/home.html')


def _can_access_document(user, document: Document):
    if user.role in {user.Roles.ADMIN, user.Roles.REVIEWER}:
        return True
    return document.signatories.filter(user=user).exists()


def _forbidden_or_login(request, message: str):
    """
    Si no hay sesión, pide login y vuelve a la URL solicitada.
    Si ya hay sesión, es falta de permisos: 403.
    """
    if not request.user.is_authenticated:
        login_url = f"{reverse('login')}?next={quote(request.get_full_path())}"
        return redirect(login_url)
    return HttpResponseForbidden(message)


@login_required
def my_profile(request):
    profile_form = UserProfileForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('portal_my_profile')

        elif action == 'change_password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Mantiene la sesión activa tras el cambio de contraseña
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('portal_my_profile')
            messages.error(request, 'No se pudo actualizar la contraseña. Revisa los datos ingresados.')

    return render(
        request,
        'portal/mi_perfil.html',
        {'form': profile_form, 'password_form': password_form},
    )


def _signatory_for(user, document: Document):
    return document.signatories.filter(user=user).first()


def _display_user_name(user):
    full = (user.get_full_name() or '').strip()
    return full or user.username


def _current_pending_signatory(document: Document):
    return document.signatories.filter(status='pending').select_related('user').order_by('sign_order', 'id').first()


def _is_fully_signed(document: Document) -> bool:
    signatories = list(document.signatories.all())
    return bool(signatories) and all(s.status == DocumentSignatory.Status.SIGNED for s in signatories)


def _build_approval_row(user, document: Document) -> dict:
    signatories = list(document.signatories.all())
    my_sig = next((s for s in signatories if s.user_id == user.id), None)
    current_pending = document.current_pending_signatory()
    rejected_signatory = document.rejected_signatory()
    fully_signed = bool(signatories) and all(s.status == DocumentSignatory.Status.SIGNED for s in signatories)
    is_my_turn = bool(
        document.status == Document.Status.PENDING
        and my_sig
        and my_sig.status == 'pending'
        and current_pending
        and current_pending.user_id == user.id
    )
    return {
        'document': document,
        'my_signatory': my_sig,
        'needs_my_signature': is_my_turn,
        'pending_by': _display_user_name(current_pending.user) if current_pending else '',
        'waiting_turn': bool(
            my_sig
            and my_sig.status == 'pending'
            and not is_my_turn
            and document.status == Document.Status.PENDING
        ),
        'rejected_by': _display_user_name(rejected_signatory.user) if rejected_signatory else '',
        'can_delete': not fully_signed,
        'delete_block_reason': 'No se puede eliminar un documento ya firmado por todos.' if fully_signed else '',
    }


def _normalize_archived_take(raw_take: int) -> int:
    """Primera carga 15; siguientes +10 (+10, ...)."""
    take = int(raw_take)
    if take <= 15:
        return 15
    return 15 + math.ceil((take - 15) / 10) * 10


def _file_to_data_url(file_obj, fallback_name='firma.png'):
    content_type = getattr(file_obj, 'content_type', None)
    if not content_type:
        name = getattr(file_obj, 'name', fallback_name)
        guessed, _ = mimetypes.guess_type(name)
        content_type = guessed or 'image/png'

    raw = file_obj.read()
    try:
        file_obj.seek(0)
    except Exception:
        pass

    encoded = base64.b64encode(raw).decode('ascii')
    return f'data:{content_type};base64,{encoded}'


def _user_has_usable_saved_signature(user) -> bool:
    """True si el usuario tiene imagen de firma y el archivo existe en almacenamiento."""
    if not getattr(user, 'signature_image', None):
        return False
    try:
        user.signature_image.open('rb')
        user.signature_image.close()
    except (FileNotFoundError, OSError):
        return False
    return True


def _sign_flow_gate(request, document):
    """
    Validaciones comunes del flujo de firma.
    Devuelve (signatory, respuesta). Si respuesta no es None, devuélvela desde la vista.
    """
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return None, _forbidden_or_login(request, 'No eres firmante de este documento.')
    if signatory.status == 'signed':
        messages.info(request, 'Ya finalizaste tu firma en este documento.')
        return None, redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'Ya rechazaste este documento.')
        return None, redirect('portal_document_detail', pk=document.id)
    if document.status != Document.Status.PENDING:
        messages.info(request, 'El documento ya no está disponible para firmar.')
        return None, redirect('portal_document_detail', pk=document.id)
    current_pending = _current_pending_signatory(document)
    if not current_pending or current_pending.user_id != request.user.id:
        pending_name = _display_user_name(current_pending.user) if current_pending else 'otro firmante'
        messages.info(request, f'Aún no es tu turno de firma. Pendiente por: {pending_name}.')
        return None, redirect('portal_document_detail', pk=document.id)
    return signatory, None


def _attempt_signature_capture_for_finalize(request, document):
    """
    Procesa el POST de firma: usa firma guardada si existe y es legible; si no, exige subida.
    Devuelve (redirect_response|None, form|None). Si redirect_response, la vista debe retornarlo.
    """
    post = request.POST.copy()
    user = request.user
    if _user_has_usable_saved_signature(user):
        post['signature_mode'] = SignatureCaptureForm.SignatureMode.SAVED
        post.setdefault('signature_data', '')
    else:
        post['signature_mode'] = SignatureCaptureForm.SignatureMode.UPLOAD

    form = SignatureCaptureForm(post, request.FILES, user=user)
    if not form.is_valid():
        return None, form

    mode = form.cleaned_data['signature_mode']
    if mode == SignatureCaptureForm.SignatureMode.SAVED:
        try:
            user.signature_image.open('rb')
            signature_data = _file_to_data_url(user.signature_image, fallback_name='firma_guardada.png')
            user.signature_image.close()
        except FileNotFoundError:
            messages.error(
                request,
                'Tu firma guardada no está disponible en almacenamiento. Sube una imagen de firma.',
            )
            return redirect('portal_sign_flow_review', pk=document.id), None
    else:
        uploaded = form.cleaned_data['signature_upload']
        signature_data = _file_to_data_url(uploaded, fallback_name=uploaded.name)
        user.signature_image = uploaded
        user.save(update_fields=['signature_image'])

    request.session['pending_signature_data'] = signature_data
    request.session['pending_signer_note'] = form.cleaned_data.get('signer_note') or ''
    return redirect('portal_sign_flow_finalize', pk=document.id), None


@login_required
def approvals_index(request):
    category_choices = list(Document.Category.choices)
    valid_categories = {value for value, _label in category_choices}
    selected_category = (request.GET.get('categoria') or '').strip()
    if selected_category and selected_category not in valid_categories:
        selected_category = ''

    query = (request.GET.get('q') or '').strip()

    documents = (
        Document.objects.select_related('uploaded_by')
        .prefetch_related('signatories__user', 'signatures__user')
        .filter(archived_at__isnull=True)
    )
    if selected_category:
        documents = documents.filter(category=selected_category)
    if query:
        documents = documents.filter(title__icontains=query)
    if request.user.role == request.user.Roles.CLIENT:
        documents = documents.filter(signatories__user=request.user).distinct()
    documents = documents.order_by('-created_at')

    all_rows = []
    pending_for_me = []
    for d in documents:
        row = _build_approval_row(request.user, d)
        all_rows.append(row)
        if row['needs_my_signature'] and d.status == Document.Status.PENDING:
            pending_for_me.append(row)

    paginator = Paginator(all_rows, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    rows = list(page_obj.object_list)
    pagination_query = urlencode(
        {k: v for k, v in {'categoria': selected_category, 'q': query}.items() if v}
    )

    return render(
        request,
        'portal/aprobaciones.html',
        {
            'rows': rows,
            'page_obj': page_obj,
            'pending_for_me': pending_for_me,
            'category_menu': category_choices,
            'selected_category': selected_category,
            'query': query,
            'pagination_query': pagination_query,
        },
    )


@login_required
def archived_documents_index(request):
    take = _normalize_archived_take(int(request.GET.get('take', 15)))

    documents = (
        Document.objects.select_related('uploaded_by', 'archived_by')
        .prefetch_related('signatories__user', 'signatures__user')
        .filter(archived_at__isnull=False)
    )
    if request.user.role == request.user.Roles.CLIENT:
        documents = documents.filter(
            Exists(DocumentSignatory.objects.filter(document_id=OuterRef('pk'), user=request.user))
        )
    documents = documents.order_by('-archived_at', '-id')

    slice_list = list(documents[: take + 1])
    has_more = len(slice_list) > take
    slice_list = slice_list[:take]

    rows = [_build_approval_row(request.user, d) for d in slice_list]
    next_take = take + 10 if has_more else None

    return render(
        request,
        'portal/archivados.html',
        {
            'rows': rows,
            'take': take,
            'next_take': next_take,
            'has_more': has_more,
        },
    )


@login_required
@require_POST
def document_archive(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    if not _can_access_document(request.user, document):
        return _forbidden_or_login(request, 'No tienes acceso a este documento.')

    if document.archived_at:
        messages.info(request, 'Este documento ya está archivado.')
        return redirect('portal_approvals_index')

    if document.status not in {
        Document.Status.APPROVED,
        Document.Status.REJECTED,
        Document.Status.SIGNED,
    }:
        messages.error(request, 'Solo puedes archivar documentos aprobados, firmados o rechazados.')
        return redirect('portal_approvals_index')

    document.archived_at = timezone.now()
    document.archived_by = request.user
    document.save(update_fields=['archived_at', 'archived_by', 'updated_at'])
    messages.success(request, 'Documento archivado.')
    return redirect('portal_approvals_index')


@login_required
@require_POST
def document_delete(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    if not _can_access_document(request.user, document):
        return _forbidden_or_login(request, 'No tienes acceso a este documento.')
    back_to_archived = '/aprobaciones/archivados/' in (request.META.get('HTTP_REFERER') or '')

    if _is_fully_signed(document):
        messages.error(request, 'No se puede eliminar un documento ya firmado por todos.')
        return redirect('portal_archived_documents' if back_to_archived else 'portal_approvals_index')

    title = document.title
    if document.file:
        document.file.delete(save=False)
    if document.signed_file:
        document.signed_file.delete(save=False)
    document.delete()
    messages.success(request, f'Documento "{title}" eliminado correctamente.')
    return redirect('portal_archived_documents' if back_to_archived else 'portal_approvals_index')


@login_required
def document_create(request):
    if request.method == 'POST':
        form = DocumentCreateForm(request.POST, request.FILES, initial={'uploader': request.user})
        if form.is_valid():
            with transaction.atomic():
                document: Document = form.save(commit=False)
                document.uploaded_by = request.user
                document.status = Document.Status.PENDING
                document.save()

                signers = list(form.cleaned_data['firmantes'])
                if form.cleaned_data.get('soy_firmante', False) and request.user not in signers:
                    signers.append(request.user)
                for index, signer in enumerate(signers, start=1):
                    document.signatories.create(user=signer, status='pending', sign_order=index)

            messages.success(request, 'Documento creado y enviado a firmantes.')
            return redirect('portal_approvals_index')
    else:
        form = DocumentCreateForm(initial={'uploader': request.user})

    return render(request, 'portal/documento_nuevo.html', {'form': form})


@login_required
def document_edit(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    if document.uploaded_by_id != request.user.id:
        return _forbidden_or_login(request, 'Solo el creador puede editar este documento.')

    if request.method == 'POST':
        form = DocumentEditForm(request.POST, instance=document)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                new_signers = list(form.cleaned_data.get('new_signers') or [])
                if new_signers:
                    last_order = document.signatories.order_by('-sign_order', '-id').values_list('sign_order', flat=True).first() or 0
                    for offset, signer in enumerate(new_signers, start=1):
                        document.signatories.create(
                            user=signer,
                            status=DocumentSignatory.Status.PENDING,
                            sign_order=last_order + offset,
                        )

            if new_signers:
                messages.success(request, 'Documento actualizado y firmantes agregados correctamente.')
            else:
                messages.success(request, 'Documento actualizado correctamente.')
            return redirect('portal_document_detail', pk=document.id)
    else:
        form = DocumentEditForm(instance=document)

    return render(
        request,
        'portal/documento_editar.html',
        {
            'document': document,
            'form': form,
        },
    )


@login_required
def document_detail(request, pk: int):
    document = get_object_or_404(
        Document.objects.select_related('uploaded_by')
        .prefetch_related('signatories__user', 'signatures__user'),
        pk=pk,
    )

    if not _can_access_document(request.user, document):
        return _forbidden_or_login(request, 'No tienes acceso a este documento.')

    my_signatory = _signatory_for(request.user, document)
    current_pending = _current_pending_signatory(document)
    rejected_signatory = document.rejected_signatory()
    is_my_turn = bool(
        document.status == Document.Status.PENDING
        and my_signatory
        and my_signatory.status == 'pending'
        and current_pending
        and current_pending.user_id == request.user.id
    )
    return render(
        request,
        'portal/documento_detalle.html',
        {
            'document': document,
            'my_signatory': my_signatory,
            'is_my_turn': is_my_turn,
            'current_pending_signatory': current_pending,
            'rejected_signatory': rejected_signatory,
        },
    )


@login_required
def document_pdf(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    if not _can_access_document(request.user, document):
        return _forbidden_or_login(request, 'No tienes acceso a este documento.')

    file_field = document.signed_file if document.signed_file else document.file
    if not file_field:
        raise Http404()

    try:
        file_field.open('rb')
    except FileNotFoundError:
        raise Http404('El archivo del documento no está disponible en almacenamiento.')
    filename = file_field.name.split('/')[-1]
    resp = FileResponse(file_field, content_type='application/pdf', as_attachment=False)
    # iOS/Safari es sensible a headers y a incrustación en iframes; inline + filename ASCII/UTF-8 ayuda.
    ascii_name = filename.encode('ascii', 'ignore').decode('ascii') or 'documento.pdf'
    utf8_name = quote(filename)
    resp['Content-Disposition'] = f'inline; filename="{ascii_name}"; filename*=UTF-8\'\'{utf8_name}'
    resp['X-Content-Type-Options'] = 'nosniff'
    # Evita respuestas cacheadas “pegadas” entre usuarios/sesiones en proxies/CDN
    resp['Cache-Control'] = 'private, no-store'
    return resp


@login_required
@xframe_options_sameorigin
def document_pdf_embed(request, pk: int):
    """
    Página HTML que renderiza el PDF con PDF.js (canvas).
    Sirve para vista previa en móviles y dentro de iframes, donde el PDF nativo suele fallar.
    """
    document = get_object_or_404(Document, pk=pk)
    if not _can_access_document(request.user, document):
        return _forbidden_or_login(request, 'No tienes acceso a este documento.')

    file_field = document.signed_file if document.signed_file else document.file
    if not file_field:
        return render(
            request,
            'portal/pdf_embed_viewer.html',
            {'error': 'no_file', 'pdf_fetch_url': '', 'document_title': document.title},
        )

    pdf_fetch_url = reverse('portal_document_pdf', args=[pk])
    return render(
        request,
        'portal/pdf_embed_viewer.html',
        {'pdf_fetch_url': pdf_fetch_url, 'document_title': document.title},
    )


@login_required
def document_signed_download(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    if not _can_access_document(request.user, document):
        return _forbidden_or_login(request, 'No tienes acceso a este documento.')

    if not document.signed_file:
        raise Http404('Este documento aún no tiene versión firmada.')

    try:
        document.signed_file.open('rb')
    except FileNotFoundError:
        raise Http404('El PDF firmado no está disponible en almacenamiento.')
    filename = document.signed_file.name.split('/')[-1]
    return FileResponse(document.signed_file, content_type='application/pdf', as_attachment=True, filename=filename)


@login_required
def document_sign_preview_pdf(request, pk: int):
    """PDF en memoria: original + notas + firmas con la firma pendiente (sin persistir)."""
    document = get_object_or_404(Document, pk=pk)
    signatory, gate = _sign_flow_gate(request, document)
    if gate:
        return gate

    pending = request.session.get('pending_signature_data')
    if not pending:
        return HttpResponse('No hay firma pendiente de confirmar.', status=400, content_type='text/plain; charset=utf-8')

    try:
        raw = build_signed_pdf_preview_bytes(
            document,
            request.user,
            pending,
            pending_signer_note=request.session.get('pending_signer_note', ''),
        )
    except (FileNotFoundError, ValueError):
        raise Http404('El PDF del documento no está disponible.')

    buf = BytesIO(raw)
    buf.seek(0)
    return FileResponse(
        buf,
        content_type='application/pdf',
        as_attachment=False,
        filename=f'vista-previa-firmado-{pk}.pdf',
    )


@login_required
@xframe_options_sameorigin
def document_sign_preview_embed(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory, gate = _sign_flow_gate(request, document)
    if gate:
        return gate

    if not request.session.get('pending_signature_data'):
        return render(
            request,
            'portal/pdf_embed_viewer.html',
            {'error': 'no_session', 'pdf_fetch_url': '', 'document_title': document.title},
        )

    pdf_fetch_url = reverse('portal_document_sign_preview_pdf', args=[pk])
    return render(
        request,
        'portal/pdf_embed_viewer.html',
        {'pdf_fetch_url': pdf_fetch_url, 'document_title': document.title},
    )


@login_required
def sign_flow_review(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory, gate = _sign_flow_gate(request, document)
    if gate:
        return gate

    if request.method == 'POST':
        redirect_resp, err_form = _attempt_signature_capture_for_finalize(request, document)
        if redirect_resp:
            return redirect_resp
        return render(
            request,
            'portal/firma_paso1.html',
            {
                'document': document,
                'signatory': signatory,
                'form': err_form,
                'has_saved_signature': _user_has_usable_saved_signature(request.user),
                'saved_signature_url': request.user.signature_image.url if request.user.signature_image else '',
            },
        )

    return render(
        request,
        'portal/firma_paso1.html',
        {
            'document': document,
            'signatory': signatory,
            'form': SignatureCaptureForm(
                user=request.user,
                initial={'signer_note': request.session.get('pending_signer_note', '')},
            ),
            'has_saved_signature': _user_has_usable_saved_signature(request.user),
            'saved_signature_url': request.user.signature_image.url if request.user.signature_image else '',
        },
    )


@login_required
def sign_flow_sign(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory, gate = _sign_flow_gate(request, document)
    if gate:
        return gate

    if request.method == 'POST':
        redirect_resp, err_form = _attempt_signature_capture_for_finalize(request, document)
        if redirect_resp:
            return redirect_resp
        return render(
            request,
            'portal/firma_paso1.html',
            {
                'document': document,
                'signatory': signatory,
                'form': err_form,
                'has_saved_signature': _user_has_usable_saved_signature(request.user),
                'saved_signature_url': request.user.signature_image.url if request.user.signature_image else '',
            },
        )

    return redirect('portal_sign_flow_review', pk=document.id)


@login_required
def sign_flow_finalize(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return _forbidden_or_login(request, 'No eres firmante de este documento.')
    if signatory.status == 'signed':
        return redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'No puedes firmar un documento que ya rechazaste.')
        return redirect('portal_document_detail', pk=document.id)
    if document.status != Document.Status.PENDING:
        messages.info(request, 'El documento ya no está disponible para firmar.')
        return redirect('portal_document_detail', pk=document.id)
    current_pending = _current_pending_signatory(document)
    if not current_pending or current_pending.user_id != request.user.id:
        pending_name = _display_user_name(current_pending.user) if current_pending else 'otro firmante'
        messages.info(request, f'Aún no es tu turno de firma. Pendiente por: {pending_name}.')
        return redirect('portal_document_detail', pk=document.id)

    signature_data = request.session.get('pending_signature_data')
    if not signature_data:
        return redirect('portal_sign_flow_review', pk=document.id)

    if request.method == 'POST':
        with transaction.atomic():
            Signature.objects.update_or_create(
                document=document,
                user=request.user,
                defaults={
                    'signature_data': signature_data,
                    'signer_note': (request.session.get('pending_signer_note') or '').strip(),
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'is_valid': True,
                },
            )
            try:
                WorkflowService.sign_document(document, request.user, ip_address=request.META.get('REMOTE_ADDR'))
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('portal_document_detail', pk=document.id)
            try:
                rebuild_signed_pdf(document)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('portal_document_detail', pk=document.id)

        request.session.pop('pending_signature_data', None)
        request.session.pop('pending_signer_note', None)
        messages.success(request, 'Firma registrada.')
        return redirect('portal_approvals_index')

    return render(
        request,
        'portal/firma_paso3.html',
        {
            'document': document,
            'signatory': signatory,
        },
    )


@login_required
def approve_entry(request, pk: int):
    """
    Punto de entrada desde el listado: manda al flujo de firma.
    """
    document = get_object_or_404(Document, pk=pk)
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return _forbidden_or_login(request, 'No eres firmante de este documento.')
    if signatory.status == 'signed':
        return redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'Ya rechazaste este documento.')
        return redirect('portal_document_detail', pk=document.id)
    current_pending = _current_pending_signatory(document)
    if document.status != Document.Status.PENDING:
        messages.info(request, 'El documento ya no está disponible para firmar.')
        return redirect('portal_document_detail', pk=document.id)
    if not current_pending or current_pending.user_id != request.user.id:
        pending_name = _display_user_name(current_pending.user) if current_pending else 'otro firmante'
        messages.info(request, f'Aún no es tu turno de firma. Pendiente por: {pending_name}.')
        return redirect('portal_document_detail', pk=document.id)
    return redirect('portal_sign_flow_review', pk=document.id)


@login_required
def reject_entry(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return _forbidden_or_login(request, 'No eres firmante de este documento.')
    if signatory.status == 'signed':
        messages.info(request, 'Ya firmaste este documento, no puedes rechazarlo.')
        return redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'Ya rechazaste este documento.')
        return redirect('portal_document_detail', pk=document.id)
    if document.status != Document.Status.PENDING:
        messages.info(request, 'El documento ya no está disponible para rechazo.')
        return redirect('portal_document_detail', pk=document.id)
    current_pending = _current_pending_signatory(document)
    if not current_pending or current_pending.user_id != request.user.id:
        pending_name = _display_user_name(current_pending.user) if current_pending else 'otro firmante'
        messages.info(request, f'Aún no es tu turno de firma. Pendiente por: {pending_name}.')
        return redirect('portal_document_detail', pk=document.id)

    form = RejectionReasonForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        reason = form.cleaned_data['reason']
        try:
            WorkflowService.reject_by_signatory(
                document=document,
                actor=request.user,
                reason=reason,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('portal_document_detail', pk=document.id)

        messages.success(request, 'Documento rechazado correctamente.')
        return redirect('portal_approvals_index')

    return render(
        request,
        'portal/rechazar_documento.html',
        {'document': document, 'signatory': signatory, 'form': form},
    )
