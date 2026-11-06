import django_filters
from jsondataferret.filters import HTML5DateInput


class HistoryFilter(django_filters.FilterSet):
    """The date range on the site-wide History page. Both dates are included: To 12 Oct takes in the whole of the 12th.

    The names (created__gt, created__lt) are what the page's addresses have always used, so old links keep working."""

    created__gt = django_filters.DateFilter(
        field_name="created",
        lookup_expr="date__gte",
        label="From",
        widget=HTML5DateInput(attrs={"class": "form-control"}),
    )
    created__lt = django_filters.DateFilter(
        field_name="created",
        lookup_expr="date__lte",
        label="To",
        widget=HTML5DateInput(attrs={"class": "form-control"}),
    )
