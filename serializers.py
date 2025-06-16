from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from api.models import Users


# rest_framework_simplejwt.token_blacklist 앱이 제공하는 **내부 모델(OutstandingToken)**에 자동으로 저장
# 회원가입
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Users
        fields = ("email", "password", "position", "phone", "user_name", "company")

    def create(self, validated_data):
        print("🔥 validated_data:", validated_data)
        # 원하는 형식으로 포맷 해서 넣으면 로그인 못함 (DB에는 str로 저장되나 지정을 DateTime으로 해놔서 Django규정때문에...)
        validated_data["join_date"] = timezone.now()
        # User 생성
        return Users.objects.create_user(**validated_data)


# 로그인
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # DB에 리프래시토큰 가장 최신 것 1개 빼고 삭제 - SimpleJWT 구조상 로그인할 때마다 row가 생김( 업데이트 불가 )
        try:
            latest_token_id = (
                OutstandingToken.objects.filter(user=user).latest("created_at").id
            )
            OutstandingToken.objects.filter(user=user).exclude(
                id=latest_token_id
            ).delete()
        except Exception as e:
            print(f"🔥 [get_token] OutstandingToken 처리 중 오류 발생: {e}")
            pass
        return token

    def validate(self, attrs):

        try:
            raw_data = super().validate(attrs)  # This gives flat
        except Exception as e:
            print("🔥 super().validate(attrs) 단계에서 Exception 발생!", e)
            raise

        print("==== 디버깅 진입 ====")
        try:
            print("self.user: ", getattr(self, "user", None))
            if hasattr(self, "user") and self.user:
                print("self.user.id: ", self.user.id)
                print("self.user.join_date: ", self.user.join_date)

            # Structure tokens
            tokens = {
                "accessToken": raw_data.get("access"),
                "refreshToken": raw_data.get("refresh"),
            }

            # Structure user info
            user = {
                "id": self.user.id,
                "name": self.user.user_name,
                "position": self.user.position,
                "phone": self.user.phone,
                "company": self.user.company,
                "join_date": self.user.join_date.strftime("%Y-%m-%d %H:%M:%S"),
            }

            return {
                "tokens": tokens,
                "user": user,
            }

        except Exception as e:
            print("🔥 Exception 발생!", e)
            raise


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = (
            "email",
            "password",
            "position",
            "phone",
            "user_name",
            "company",
            "join_date",
        )
        extra_kwargs = {
            "password": {"write_only": True},  # password는 write_only로 처리
            "email": {"read_only": True},  # 수정불가
            "join_date": {"read_only": True},
        }

    def update(self, instance, validated_data):
        # 비밀번호는 반드시 set_password 사용해서 암호화 저장
        if "password" in validated_data:
            instance.set_password(validated_data.pop("password"))
        # 나머지 필드는 그대로 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
