from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),

    # Support with AND without trailing slash
    path("api/auth/token", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair_slash"),
    path("api/auth/token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh_slash"),
]
