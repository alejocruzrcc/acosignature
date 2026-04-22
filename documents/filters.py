import django_filters

from .models import Document


class DocumentFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='uploaded_by_id')
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = Document
        fields = ['status', 'user', 'date_from', 'date_to']
