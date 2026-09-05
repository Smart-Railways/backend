from rest_framework.pagination import PageNumberPagination


class TrainSchedulePagination(PageNumberPagination):
    """
    Pagination class for train schedules.
    Default page size is 20, customizable via query parameter ?page_size=N up to 100.
    """
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
