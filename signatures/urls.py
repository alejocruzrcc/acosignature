from django.urls import path

from .views import DocumentSignatureListView, SignDocumentView

urlpatterns = [
    path('sign/', SignDocumentView.as_view(), name='sign_document'),
    path('document/<int:id>/', DocumentSignatureListView.as_view(), name='document_signature_list'),
]
