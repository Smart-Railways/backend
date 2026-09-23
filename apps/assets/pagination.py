from rest_framework.pagination import PageNumberPagination


class AssetPagination(PageNumberPagination):
    """Pagination for the assets table endpoint."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
