"""Shared by the admin and public list pages, so both are built the same way from the same template
(indigo/includes/list_page.html)."""
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.urls import reverse

PAGE_SIZE = 100


def paginate(request, items):
    """Splits a long list into pages.

    Returns the page (which can be looped over like the list, and has page_numbers for the links under the list), and
    the rest of the query string so that links to other pages keep things like a search."""
    if not hasattr(items, "order_by"):
        # Not a normal queryset (eg a raw query, or a list), so load it so the paginator can count it
        items = list(items)
    paginator = Paginator(items, PAGE_SIZE)
    try:
        page = paginator.page(request.GET.get("page"))
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    # The page numbers to show: the first and last, the ones near this page, and "…" for the gaps
    page.page_numbers = list(
        paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1)
    )
    other_params = request.GET.copy()
    other_params.pop("page", None)
    return page, other_params.urlencode()


def search_filter(search_term, data_field, keys):
    """Matches the ID, or the value of any of these keys in the data (ignoring case).

    data_field is the JSON field to look in: use data_public on public pages so a search can never find
    something that is private."""
    search_filter = Q(public_id__icontains=search_term)
    for key in keys:
        search_filter |= Q(**{f"{data_field}__{key}__value__icontains": search_term})
    return search_filter


def visible_menu(user, groups):
    """The dropdown menu a user gets, from groups of {"heading": str or None, "items": [{"label", "url_name",
    "url_kwargs" (optional, for a link to one record), "admin_only" (optional)}]}.

    Anything they may not use is left out, and so are groups left with nothing in. Each item gets its "url"."""
    is_admin = user.has_perm("indigo.admin")
    menu = []
    for group in groups or []:
        items = [
            {**i, "url": reverse(i["url_name"], kwargs=i.get("url_kwargs"))}
            for i in group["items"]
            if is_admin or not i.get("admin_only")
        ]
        if items:
            menu.append(
                {
                    "heading": group.get("heading"),
                    "items": items,
                    "notes": group.get("notes", []),
                }
            )
    return menu


def _name_of(item, data_field):
    data = getattr(item, data_field, None)
    name = data.get("name") if isinstance(data, dict) else None
    return name.get("value", "") if isinstance(name, dict) else ""


def list_context(
    request,
    items,
    *,
    title,
    noun_plural,
    name_field,
    index_url_name,
    list_url_name,
    items_key=None,
    search_term="",
    searchable=False,
    search_placeholder="",
    edit_url_name=None,
    add_url_name=None,
    add_label="",
    menu_groups=None,
    menu_label="More",
    menu_icon="",
    search_extra_template=None,
    breadcrumbs=None,
):
    """Everything indigo/includes/list_page.html needs.

    items is the whole (already filtered) list. name_field is the JSON field on each item that has its name."""
    page_obj, pagination_get_params = paginate(request, items)
    for item in page_obj:
        item.display_name = _name_of(item, name_field)
    context = {
        "list_title": title,
        "noun_plural": noun_plural,
        "items": page_obj,
        "page_obj": page_obj,
        "pagination_get_params": pagination_get_params,
        "index_url_name": index_url_name,
        "list_url_name": list_url_name,
        "edit_url_name": edit_url_name,
        "add_url_name": add_url_name,
        "add_label": add_label,
        "menu": visible_menu(request.user, menu_groups),
        "menu_label": menu_label,
        "menu_icon": menu_icon,
        "searchable": searchable,
        "search_term": search_term,
        "search_placeholder": search_placeholder,
        "search_extra_template": search_extra_template,
        "breadcrumbs": breadcrumbs,
    }
    if items_key:
        # The same list under another name, for pages that have always had it by that name
        context[items_key] = page_obj
    return context
