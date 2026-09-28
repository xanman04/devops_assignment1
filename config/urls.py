from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from discovery.views import map_events


def index(request):
    return JsonResponse({
        "project": "Music Event Discovery",
        "status": "backend services",
        "detail": "Discovery and group services, admin moderation, and map search are ready; public pages remain pending.",
    })


urlpatterns = [path("", index), path("admin/", admin.site.urls), path("api/map/events/", map_events)]
