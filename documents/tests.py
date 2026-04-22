from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Document, DocumentSignatory
from signatures.models import Signature

User = get_user_model()


class DocumentFlowTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username='cliente', password='Pass12345!', role='client')
        self.reviewer_user = User.objects.create_user(username='reviewer', password='Pass12345!', role='reviewer')
        self.other_user = User.objects.create_user(username='firmante2', password='Pass12345!', role='client')

    def authenticate(self, username, password):
        token = self.client.post('/api/auth/login/', {'username': username, 'password': password}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")

    def test_create_document_pending(self):
        self.authenticate('cliente', 'Pass12345!')
        f = SimpleUploadedFile('doc.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        response = self.client.post('/api/documents/', {
            'title': 'Contrato',
            'description': 'Desc',
            'file': f,
            'requires_signature': True,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Document.Status.PENDING)

    def test_sign_updates_document_status(self):
        doc = Document.objects.create(
            title='Doc',
            description='Desc',
            file=SimpleUploadedFile('x.pdf', b'%PDF', content_type='application/pdf'),
            uploaded_by=self.client_user,
        )
        self.authenticate('cliente', 'Pass12345!')
        response = self.client.post('/api/signatures/sign/', {
            'document': doc.id,
            'signature_data': 'base64-data',
        }, format='json')
        doc.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(doc.status, Document.Status.SIGNED)
        self.assertTrue(Signature.objects.filter(document=doc, user=self.client_user).exists())

    def test_reviewer_approve(self):
        doc = Document.objects.create(
            title='Doc',
            description='Desc',
            file=SimpleUploadedFile('z.pdf', b'%PDF', content_type='application/pdf'),
            uploaded_by=self.client_user,
            status=Document.Status.SIGNED,
        )
        self.authenticate('reviewer', 'Pass12345!')
        response = self.client.post(f'/api/documents/{doc.id}/approve/')
        doc.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(doc.status, Document.Status.APPROVED)

    def test_multi_signatory_requires_all_signatures(self):
        doc = Document.objects.create(
            title='Doc',
            description='Desc',
            file=SimpleUploadedFile('m.pdf', b'%PDF', content_type='application/pdf'),
            uploaded_by=self.client_user,
        )
        DocumentSignatory.objects.create(document=doc, user=self.client_user, status=DocumentSignatory.Status.PENDING)
        DocumentSignatory.objects.create(document=doc, user=self.other_user, status=DocumentSignatory.Status.PENDING)

        self.authenticate('cliente', 'Pass12345!')
        r1 = self.client.post('/api/signatures/sign/', {'document': doc.id, 'signature_data': 'sig1'}, format='json')
        doc.refresh_from_db()
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(doc.status, Document.Status.PENDING)

        self.authenticate('firmante2', 'Pass12345!')
        r2 = self.client.post('/api/signatures/sign/', {'document': doc.id, 'signature_data': 'sig2'}, format='json')
        doc.refresh_from_db()
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(doc.status, Document.Status.APPROVED)
