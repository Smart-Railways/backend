from rest_framework.pagination import PageNumberPagination


class MaintenanceTaskPagination(PageNumberPagination):
    """Pagination for the maintenance table endpoint."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
