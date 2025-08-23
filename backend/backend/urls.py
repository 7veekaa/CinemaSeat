from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),


    path("api/auth/token", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair_slash"),
    path("api/auth/token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh_slash"),

    path("api/users/", include("users.urls")),  
    path("api/cinema/", include("cinema.urls")),  
]
