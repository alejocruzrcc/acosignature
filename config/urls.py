from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import CurrentUserView, CustomTokenObtainPairView
from portal import views as portal_views

urlpatterns = [
    path('', portal_views.home, name='portal_home'),
    path(
        'login/',
        LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True),
        name='login',
    ),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('mi-perfil/', portal_views.my_profile, name='portal_my_profile'),
    path('aprobaciones/', portal_views.approvals_index, name='portal_approvals_index'),
    path('aprobaciones/nuevo/', portal_views.document_create, name='portal_document_create'),
    path('aprobaciones/<int:pk>/', portal_views.document_detail, name='portal_document_detail'),
    path('aprobaciones/<int:pk>/pdf/', portal_views.document_pdf, name='portal_document_pdf'),
    path('aprobaciones/<int:pk>/pdf-firmado/', portal_views.document_signed_download, name='portal_document_signed_download'),
    path('aprobaciones/<int:pk>/aprobar/', portal_views.approve_entry, name='portal_approve_entry'),
    path('aprobaciones/<int:pk>/firmar/', portal_views.sign_flow_review, name='portal_sign_flow_review'),
    path('aprobaciones/<int:pk>/firmar/firma/', portal_views.sign_flow_sign, name='portal_sign_flow_sign'),
    path('aprobaciones/<int:pk>/firmar/finalizar/', portal_views.sign_flow_finalize, name='portal_sign_flow_finalize'),
    path('admin/', admin.site.urls),
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/me/', CurrentUserView.as_view(), name='auth_me'),
    path('api/users/', include('accounts.urls')),
    path('api/documents/', include('documents.urls')),
    path('api/signatures/', include('signatures.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
