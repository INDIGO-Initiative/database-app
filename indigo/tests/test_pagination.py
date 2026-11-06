import re

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from indigo.listpages import paginate


def _render(items, query):
    request = RequestFactory().get("/list", query)
    page_obj, params = paginate(request, list(range(items)))
    html = render_to_string(
        "indigo/includes/pagination.html",
        {"page_obj": page_obj, "pagination_get_params": params},
    )
    return page_obj, html


def _numbers(html):
    return re.findall(
        r'<li class="page-item[^"]*"[^>]*><(?:a|span)[^>]*>(\d+|…)</', html
    )


class PaginationLinksTests(SimpleTestCase):
    def test_nothing_is_shown_for_a_single_page(self):
        _, html = _render(100, {})
        self.assertNotIn("page-link", html)

    def test_a_few_pages_are_all_listed_with_the_current_one_marked(self):
        _, html = _render(250, {"page": 2})
        self.assertEqual(_numbers(html), ["1", "2", "3"])
        self.assertIn(
            'class="page-item active" aria-current="page"><span class="page-link">2<',
            html,
        )
        self.assertIn("Page 2 of 3", html)

    def test_many_pages_are_shortened_with_gaps(self):
        page, html = _render(2000, {"page": 10})
        self.assertEqual(page.number, 10)
        self.assertEqual(
            _numbers(html), ["1", "…", "8", "9", "10", "11", "12", "…", "20"]
        )

    def test_the_first_page_has_no_previous_and_the_last_has_no_next(self):
        _, first = _render(250, {})
        self.assertIn(
            '<li class="page-item disabled"><span class="page-link">&laquo; Previous',
            first,
        )
        self.assertIn('rel="next"', first)
        _, last = _render(250, {"page": 3})
        self.assertIn(
            '<li class="page-item disabled"><span class="page-link">Next &raquo;', last
        )
        self.assertIn('rel="prev"', last)

    def test_other_query_parameters_are_kept_in_the_links(self):
        _, html = _render(250, {"search": "wind & solar", "page": 1})
        self.assertIn("?search=wind+%26+solar&amp;page=2", html)
        _, plain = _render(250, {})
        self.assertIn('href="?page=2"', plain)
