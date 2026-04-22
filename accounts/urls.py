from django.urls import path

from .views import CurrentUserView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user_register'),
    path('me/', CurrentUserView.as_view(), name='user_me'),
]
