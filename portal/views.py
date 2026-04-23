from __future__ import annotations

import base64
import mimetypes
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from documents.models import Document
from documents.services import rebuild_signed_pdf
from signatures.models import Signature
from workflows.services import WorkflowService

from .forms import DocumentCreateForm, RejectionReasonForm, SignatureCaptureForm, UserProfileForm


def home(request):
    return render(request, 'portal/home.html')


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


@login_required
def approvals_index(request):
    documents = (
        Document.objects.filter(Q(uploaded_by=request.user) | Q(signatories__user=request.user))
        .select_related('uploaded_by')
        .prefetch_related('signatories__user', 'signatures__user')
        .distinct()
        .order_by('-created_at')
    )

    rows = []
    pending_for_me = []
    for d in documents:
        my_sig = next((s for s in d.signatories.all() if s.user_id == request.user.id), None)
        row = {
            'document': d,
            'my_signatory': my_sig,
            'needs_my_signature': bool(my_sig and my_sig.status == 'pending'),
        }
        rows.append(row)
        if row['needs_my_signature']:
            pending_for_me.append(d)

    return render(
        request,
        'portal/aprobaciones.html',
        {
            'rows': rows,
            'pending_for_me': pending_for_me,
        },
    )


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
                for signer in signers:
                    document.signatories.create(user=signer, status='pending')

            messages.success(request, 'Documento creado y enviado a firmantes.')
            return redirect('portal_approvals_index')
    else:
        form = DocumentCreateForm(initial={'uploader': request.user})

    return render(request, 'portal/documento_nuevo.html', {'form': form})


@login_required
def document_detail(request, pk: int):
    document = get_object_or_404(
        Document.objects.select_related('uploaded_by')
        .prefetch_related('signatories__user', 'signatures__user'),
        pk=pk,
    )

    if not document.signatories.filter(user=request.user).exists() and document.uploaded_by_id != request.user.id:
        return HttpResponseForbidden('No tienes acceso a este documento.')

    my_signatory = _signatory_for(request.user, document)
    return render(
        request,
        'portal/documento_detalle.html',
        {
            'document': document,
            'my_signatory': my_signatory,
        },
    )


@login_required
def document_pdf(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    if not document.signatories.filter(user=request.user).exists() and document.uploaded_by_id != request.user.id:
        return HttpResponseForbidden('No tienes acceso a este documento.')

    file_field = document.signed_file if document.signed_file else document.file
    if not file_field:
        raise Http404()

    file_field.open('rb')
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
def document_signed_download(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    if not document.signatories.filter(user=request.user).exists() and document.uploaded_by_id != request.user.id:
        return HttpResponseForbidden('No tienes acceso a este documento.')

    if not document.signed_file:
        raise Http404('Este documento aún no tiene versión firmada.')

    document.signed_file.open('rb')
    filename = document.signed_file.name.split('/')[-1]
    return FileResponse(document.signed_file, content_type='application/pdf', as_attachment=True, filename=filename)


@login_required
def sign_flow_review(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return HttpResponseForbidden('No eres firmante de este documento.')
    if signatory.status == 'signed':
        messages.info(request, 'Ya finalizaste tu firma en este documento.')
        return redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'Ya rechazaste este documento.')
        return redirect('portal_document_detail', pk=document.id)

    if request.method == 'POST':
        return redirect('portal_sign_flow_sign', pk=document.id)

    return render(
        request,
        'portal/firma_paso1.html',
        {
            'document': document,
            'signatory': signatory,
        },
    )


@login_required
def sign_flow_sign(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return HttpResponseForbidden('No eres firmante de este documento.')
    if signatory.status == 'signed':
        return redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'No puedes firmar un documento que ya rechazaste.')
        return redirect('portal_document_detail', pk=document.id)

    form = SignatureCaptureForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        mode = form.cleaned_data['signature_mode']

        if mode == SignatureCaptureForm.SignatureMode.DRAW:
            signature_data = form.cleaned_data['signature_data']
        elif mode == SignatureCaptureForm.SignatureMode.SAVED:
            request.user.signature_image.open('rb')
            signature_data = _file_to_data_url(request.user.signature_image, fallback_name='firma_guardada.png')
            request.user.signature_image.close()
        else:
            uploaded = form.cleaned_data['signature_upload']
            signature_data = _file_to_data_url(uploaded, fallback_name=uploaded.name)
            # Guarda la firma subida para siguientes firmas del usuario
            request.user.signature_image = uploaded
            request.user.save(update_fields=['signature_image'])

        request.session['pending_signature_data'] = signature_data
        return redirect('portal_sign_flow_finalize', pk=document.id)

    return render(
        request,
        'portal/firma_paso2.html',
        {
            'document': document,
            'signatory': signatory,
            'form': form,
            'has_saved_signature': bool(request.user.signature_image),
            'saved_signature_url': request.user.signature_image.url if request.user.signature_image else '',
        },
    )


@login_required
def sign_flow_finalize(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return HttpResponseForbidden('No eres firmante de este documento.')
    if signatory.status == 'signed':
        return redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'No puedes firmar un documento que ya rechazaste.')
        return redirect('portal_document_detail', pk=document.id)

    signature_data = request.session.get('pending_signature_data')
    if not signature_data:
        return redirect('portal_sign_flow_sign', pk=document.id)

    if request.method == 'POST':
        with transaction.atomic():
            Signature.objects.update_or_create(
                document=document,
                user=request.user,
                defaults={
                    'signature_data': signature_data,
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'is_valid': True,
                },
            )
            WorkflowService.sign_document(document, request.user, ip_address=request.META.get('REMOTE_ADDR'))
            rebuild_signed_pdf(document)

        request.session.pop('pending_signature_data', None)
        messages.success(request, 'Firma registrada.')
        return redirect('portal_document_detail', pk=document.id)

    return render(
        request,
        'portal/firma_paso3.html',
        {
            'document': document,
            'signatory': signatory,
            'signature_preview': signature_data,
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
        return HttpResponseForbidden('No eres firmante de este documento.')
    if signatory.status == 'signed':
        return redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'Ya rechazaste este documento.')
        return redirect('portal_document_detail', pk=document.id)
    return redirect('portal_sign_flow_review', pk=document.id)


@login_required
def reject_entry(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return HttpResponseForbidden('No eres firmante de este documento.')
    if signatory.status == 'signed':
        messages.info(request, 'Ya firmaste este documento, no puedes rechazarlo.')
        return redirect('portal_document_detail', pk=document.id)
    if signatory.status == 'rejected':
        messages.info(request, 'Ya rechazaste este documento.')
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
