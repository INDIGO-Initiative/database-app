from django.conf import settings


class TemplateContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.app_title = settings.APP_TITLE
        # This should be in function as below, but I couldn't get that to work and it doesn't really matter
        response = self.get_response(request)
        return response

    # def process_template_response(self, request, response):
    #    response.context_data["app_title"] = settings.APP_TITLE
    #    return response
