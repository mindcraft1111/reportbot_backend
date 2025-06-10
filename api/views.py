from django.shortcuts import render
from .models import Users

from serializers import RegisterSerializer
from serializers import CustomTokenObtainPairSerializer
from serializers import UpdateUserSerializer

from rest_framework import generics, permissions
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.permissions import IsAuthenticated



class RegisterView(generics.CreateAPIView): # 회원가입 CreateAPIView는 POST 요청을 처리하기 때문에 따로 post() 메서드를 정의할 필요가 없습니다.
    queryset = Users.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    

"""
로그아웃은 프론트에서 Refresh 토큰을 보내면 서버에서 Refresh 토큰을 블랙리스트 처리만
로그인 하면 클라이언트는 두개의 토큰 모두저장함
프론트에서 보내주면 자체적으로 처리
* 프론트는 가능한 경우 Refresh 토큰을 HttpOnly Cookie에 저장하는 것이 안전
"""
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # 프론트에서 바디에 refresh있어야함 ( "refresh" : "리프레쉐 토큰")

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"detail": "Refresh token is required."}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "로그아웃"},status=204)
        except TokenError as e:
            return Response({"detail": str(e)}, status=400)
        except Exception:
            return Response({"detail": "Invalid request."}, status=400)
        
                
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class DeleteUserView(APIView):  # 프론트에서 헤더에 access_token있어야함
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"detail": "회원 탈퇴가 완료되었습니다."}, status=status.HTTP_204_NO_CONTENT)



class UpdateUserView(APIView):
    permission_classes = [IsAuthenticated]  # 프론트에서 헤더에 access_token있어야함 

    def put(self, request):
        user = request.user  # 현재 로그인한 사용자 가져오기
        serializer = UpdateUserSerializer(user, data=request.data, partial=True)  # partial=True로 하면 일부만 수정 가능
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "회원정보가 성공적으로 수정되었습니다."}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
