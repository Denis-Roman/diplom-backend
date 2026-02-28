from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static

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