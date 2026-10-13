from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import RedirectView


def index(request):
    return redirect("/app")


class RetiredPageRedirect(RedirectView):
    """For addresses that no longer have a page: send visitors to the admin home page, whatever the rest of the
    address was."""

    def get_redirect_url(self, *args, **kwargs):
        return reverse("indigo_admin_index")
