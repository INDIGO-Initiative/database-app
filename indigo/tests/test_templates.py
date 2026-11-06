import glob
import os
import re

from django.test import SimpleTestCase  # noqa


class ViewButtonTests(SimpleTestCase):
    def test_every_view_button_in_a_table_is_small(self):
        """View buttons sit in table rows, so they are all the small size (btn-sm), whichever page they are on."""
        root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        found = 0
        for path in glob.glob(os.path.join(root, "**", "*.html"), recursive=True):
            with open(path) as fp:
                for number, line in enumerate(fp, start=1):
                    # (The "View project" button in the header of the moderation page is not in a table)
                    if re.search(r">View[^<]*</a>", line) and "{{ noun }}" not in line:
                        found += 1
                        self.assertIn(
                            "btn-sm",
                            line,
                            f"{os.path.relpath(path, root)} line {number} has a View button that is not btn-sm",
                        )
        # The check would pass quietly if the buttons were all removed, so make sure it is looking at something
        self.assertGreater(found, 10)


class LibraryPagesTests(SimpleTestCase):
    def test_nothing_in_the_app_links_to_the_json_data_ferret_pages(self):
        """The library's own pages are not switched on, so nothing may link to them (they would be dead links)."""
        base = os.path.dirname(os.path.dirname(__file__))
        paths = glob.glob(
            os.path.join(base, "templates", "**", "*.html"), recursive=True
        )
        paths += [
            p
            for p in glob.glob(os.path.join(base, "*.py"))
            if not p.endswith("tests.py")
        ]
        for path in paths:
            with open(path) as fp:
                text = fp.read()
            self.assertNotIn(
                "jsondataferret_",
                text.replace("jsondataferret_retired", ""),
                f"{os.path.relpath(path, base)} uses one of the library's own pages",
            )
