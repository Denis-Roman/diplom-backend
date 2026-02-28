from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

def api_root(request):
    return JsonResponse({
        'message': 'Django Backend API is running',
        'endpoints': {
            'admin': '/admin/',
            'login': '/api/auth/login/',
            'register': '/api/auth/register/',
        }
    })

urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', include('school.urls')),

]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.MEDIA_URL and not settings.DEBUG:
    media_prefix = settings.MEDIA_URL.lstrip('/')
    media_pattern = rf'^{media_prefix}(?P<path>.*)$'
    urlpatterns += [
        re_path(media_pattern, serve, {'document_root': settings.MEDIA_ROOT}),
    ]