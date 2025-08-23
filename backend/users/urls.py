from django.urls import path
from .views import health, ping, RegisterView, MeView

urlpatterns = [

    path("health/", health, name="health"),
    path("ping/", ping, name="ping"),


    path("register/", RegisterView.as_view(), name="register"),  
    path("me/", MeView.as_view(), name="me"),                    
]
