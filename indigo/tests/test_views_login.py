from django.contrib.auth.models import User
from django.test import TestCase  # noqa
from django.urls import reverse


class LoginPageTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="martin", password="correct-horse")

    def test_the_page_is_a_styled_form_with_the_username_ready_to_type_in(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h2 class="mb-4">Log in</h2>')
        self.assertContains(response, 'class="form-control"', count=2)
        self.assertContains(response, "autofocus")
        self.assertContains(response, "btn btn-primary btn-block")
        # No alerts before anything has gone wrong
        self.assertNotContains(response, "alert-danger")
        self.assertNotContains(response, "alert-info")

    def test_the_top_bar_does_not_offer_login_on_the_login_page(self):
        response = self.client.get(reverse("login"))
        self.assertNotContains(response, "btn-outline-light")
        # But does elsewhere
        self.assertContains(
            self.client.get(reverse("indigo_index")), "btn-outline-light"
        )

    def test_a_wrong_password_says_so_and_keeps_the_username(self):
        response = self.client.post(
            reverse("login"), {"username": "martin", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alert-danger")
        self.assertContains(response, "didn't match")
        self.assertContains(response, 'value="martin"')

    def test_logging_in_goes_to_the_site_or_where_you_were_going(self):
        response = self.client.post(
            reverse("login"), {"username": "martin", "password": "correct-horse"}
        )
        self.assertRedirects(response, "/app/", fetch_redirect_response=False)
        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {
                "username": "martin",
                "password": "correct-horse",
                "next": reverse("indigo_project_list"),
            },
        )
        self.assertRedirects(
            response, reverse("indigo_project_list"), fetch_redirect_response=False
        )

    def test_being_sent_here_explains_why(self):
        # Sent here from the admin without being logged in
        response = self.client.get(reverse("indigo_admin_index"), follow=True)
        self.assertContains(response, "Please log in to see that page")
        # Logged in, but without the permission for the page
        self.client.login(username="martin", password="correct-horse")
        response = self.client.get(reverse("indigo_admin_to_moderate"), follow=True)
        self.assertContains(response, "doesn't have access to that page")

    def test_the_logged_out_page_is_styled_and_offers_login(self):
        self.client.login(username="martin", password="correct-horse")
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You have been logged out")
        self.assertContains(response, reverse("login"))
        self.assertContains(response, 'class="site-header__title"')
