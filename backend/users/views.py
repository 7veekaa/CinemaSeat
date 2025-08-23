# backend/users/views.py
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

UserModel = get_user_model()

def ok(data, code=status.HTTP_200_OK):
    return Response(data, status=code)

# ---------- health ----------
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return ok({"status": "ok", "service": "users"})

@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    return ok({"pong": True, "now": timezone.now()})

# ---------- register ----------
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"detail": "username & password required"}, status=400)
        if UserModel.objects.filter(username=username).exists():
            return Response({"detail": "username taken"}, status=409)
        user = UserModel.objects.create_user(username=username, password=password)
        return ok({"id": user.id, "username": user.username}, code=status.HTTP_201_CREATED)

# ---------- me ----------
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return ok({"id": u.id, "username": u.username, "email": getattr(u, "email", "")})
