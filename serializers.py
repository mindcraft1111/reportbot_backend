from rest_framework import serializers
from api.models import Users
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

# rest_framework_simplejwt.token_blacklist 앱이 제공하는 **내부 모델(OutstandingToken)**에 자동으로 저장
# 회원가입
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Users
        fields = ('user_id', 'password', 'email', 'company', 'position', 'phone', 'user_name', 'join_date')

    def create(self, validated_data):
        return Users.objects.create_user(**validated_data)
    

# 로그인
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # 추가로 응답에 사용자 정보 포함 가능
        token['id'] = user.id
        token['user_id_text'] = user.user_id  # 👈 별도 키로 사용

        # DB에 리프래시토큰 가장 최신 것 1개 빼고 삭제 - SimpleJWT 구조상 로그인할 때마다 row가 생김( 업데이트 불가 )
        try:
            latest_token_id = OutstandingToken.objects.filter(user=user).latest('created_at').id
            OutstandingToken.objects.filter(user=user).exclude(id=latest_token_id).delete()
        except:
            pass  # 오류 발생 시 무시 (예: 처음 로그인할 때 등)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # 토큰 이외에 사용자 정보도 응답하고 싶을 경우:
        data['id'] = self.user.id
        data['user_id_text'] = self.user.user_id
        return data


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('user_id', 'password', 'email', 'company', 'position', 'phone', 'user_name', 'join_date')
        extra_kwargs = {
            'password': {'write_only': True},  # password는 write_only로 처리
            'user_id': {'read_only': True}, # 수정불가
            'join_date': {'read_only': True}, 
        }

    def update(self, instance, validated_data):
        # 비밀번호는 반드시 set_password 사용해서 암호화 저장
        if 'password' in validated_data:
            instance.set_password(validated_data.pop('password'))
        # 나머지 필드는 그대로 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance