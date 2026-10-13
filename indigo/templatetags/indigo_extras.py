import re

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Only web addresses are linked, so nothing like javascript: can be made into a link
URL_RE = re.compile(r"(https?://[^\s<>\"']+)")


def _split_trailing_punctuation(url):
    """A web address at the end of a sentence does not include the full stop, comma, or a bracket that is not its own."""
    trailing = ""
    while url and (
        url[-1] in ".,;:!?" or (url[-1] == ")" and url.count("(") < url.count(")"))
    ):
        trailing = url[-1] + trailing
        url = url[:-1]
    return url, trailing


@register.filter
def linkify(value):
    """Makes the web addresses in a value into links that open in a new tab. Everything else is escaped as normal."""
    parts = URL_RE.split(str(value))
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(escape(part))
            continue
        url, trailing = _split_trailing_punctuation(part)
        if url in ("http://", "https://"):
            out.append(escape(part))
            continue
        out.append(
            format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>{}',
                url,
                url,
                trailing,
            )
        )
    return mark_safe("".join(out))


@register.simple_tag
def static_if_exists(path):
    """The URL of a static file, or nothing if there is no such file (so a page can leave out an image that has not been
    added yet instead of showing a broken one)."""
    return static(path) if finders.find(path) else ""
