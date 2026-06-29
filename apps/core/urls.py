from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("ping/", views.ping, name="ping"),
    path("media/", views.media_retrieve, name="media-retrieve"),
    # TODO 🚫 Remove the route bellow, the view, and the task.
    path("fire-task/", views.fire_task, name="fire_task"),
]
