from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse

class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if isinstance(response, HttpResponse):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
