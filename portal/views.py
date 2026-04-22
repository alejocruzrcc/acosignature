from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from documents.models import Document
from signatures.models import Signature
from workflows.services import WorkflowService

from .forms import DocumentCreateForm, SignatureCaptureForm


def home(request):
    return render(request, 'portal/home.html')


def _signatory_for(user, document: Document):
    return document.signatories.filter(user=user).first()


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

    if not document.file:
        raise Http404()

    document.file.open('rb')
    filename = document.file.name.split('/')[-1]
    resp = FileResponse(document.file, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{filename}"'
    return resp


@login_required
def sign_flow_review(request, pk: int):
    document = get_object_or_404(Document, pk=pk)
    signatory = _signatory_for(request.user, document)
    if not signatory:
        return HttpResponseForbidden('No eres firmante de este documento.')
    if signatory.status == 'signed':
        messages.info(request, 'Ya finalizaste tu firma en este documento.')
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

    form = SignatureCaptureForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        request.session['pending_signature_data'] = form.cleaned_data['signature_data']
        return redirect('portal_sign_flow_finalize', pk=document.id)

    return render(
        request,
        'portal/firma_paso2.html',
        {
            'document': document,
            'signatory': signatory,
            'form': form,
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
    return redirect('portal_sign_flow_review', pk=document.id)
