from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.query import QuerySet


def paginated_queryset(objects: list | QuerySet, page: int = 1, count: int = 10) -> dict:
    paginator = Paginator(objects, count)
    
    try:
        queryset = paginator.page(page)

    except PageNotAnInteger:
        queryset = paginator.page(1)

    except EmptyPage:
        queryset = paginator.page(paginator.num_pages)


    pages = list(paginator.get_elided_page_range(queryset.number, on_each_side=2, on_ends=1))

    next_page = queryset.next_page_number() if queryset.has_next() else None
    previous_page = queryset.previous_page_number() if queryset.has_previous() else None

    result = {
        'queryset': queryset,
        'this_page': queryset.number,
        'next_page': next_page,
        'previous_page': previous_page,
        'pages': pages,
        'visible': len(pages) > 1,
        'ellipsis': queryset.paginator.ELLIPSIS
    }
    
    return result