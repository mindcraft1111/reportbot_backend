from rest_framework import serializers
from api.models import Users
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.utils import timezone

# rest_framework_simplejwt.token_blacklist 앱이 제공하는 **내부 모델(OutstandingToken)**에 자동으로 저장
# 회원가입
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Users
        fields = ('email', 'password', 'position', 'phone', 'user_name', 'company')

    def create(self, validated_data):
        print("🔥 validated_data:", validated_data)
        # 원하는 형식으로 포맷 해서 넣으면 로그인 못함 (DB에는 str로 저장되나 지정을 DateTime으로 해놔서 Django규정때문에...)
        validated_data['join_date'] = timezone.now()
        # User 생성
        return Users.objects.create_user(**validated_data)

    

# 로그인
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # 추가로 응답에 사용자 정보 포함 가능
        token['id'] = user.id
        # DB에 리프래시토큰 가장 최신 것 1개 빼고 삭제 - SimpleJWT 구조상 로그인할 때마다 row가 생김( 업데이트 불가 )
        try:
            latest_token_id = OutstandingToken.objects.filter(user=user).latest('created_at').id
            OutstandingToken.objects.filter(user=user).exclude(id=latest_token_id).delete()
        except Exception as e:
            print(f"🔥 [get_token] OutstandingToken 처리 중 오류 발생: {e}")
            pass
        return token

    def validate(self, attrs):
        print("==== validate() 호출됨 ====")
        print("attrs: ", attrs)
        try:
            data = super().validate(attrs)
        except Exception as e:
            print("🔥 super().validate(attrs) 단계에서 Exception 발생!", e)
            raise  # 반드시 다시 raise 해줘야 정상적인 에러 응답 가능

        # 디버깅용 print 추가
        print("==== 디버깅 진입 ====")
        try:
            print("self.user: ", getattr(self, 'user', None))
            if hasattr(self, 'user') and self.user:
                print("self.user.id: ", self.user.id)
                print("self.user.join_date: ", self.user.join_date)
        except Exception as e:
            print("🔥 Exception 발생!", e)




        # 토큰 이외에 사용자 정보도 응답하고 싶을 경우:
        data['id'] = self.user.id

        data['join_date'] = self.user.join_date.strftime('%Y-%m-%d %H:%M:%S')
        return data


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('email', 'password', 'position', 'phone', 'user_name', 'company', 'join_date')
        extra_kwargs = {
            'password': {'write_only': True},  # password는 write_only로 처리
            'email': {'read_only': True}, # 수정불가
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