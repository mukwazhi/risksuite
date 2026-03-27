from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('riskregister/', include('riskregister.urls')),  # include app urls
]