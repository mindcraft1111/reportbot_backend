from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager

"""
# 장고 admin 기능 사용할려면 모든 테이블 있어야함 ( 개발중 어느 기능이 안될 수있음 ......)
변경하고
python manage.py makemigrations app_name : 해당앱만 테이블 생성 / app_name 없으면 모든 테이블 생성
setings.py에 AUTH_USER_MODEL = 'users.Users' 추가
그리고 마이그레이션을 적용합니다.
python manage.py migrate app_name
"""
"""
User모델 커스터마이징 하는 방법
1.User모델과 일대일 관계를 가지는 모델 생성
    class Employee(models.Model):
        user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
        company = models.CharField(max_length=100)
    ㄴ 단! 기존 정보는 그대로 남아있음 그래서 User모델을 그대로 이용해야 하기 때문에 email로만 로그인

2.AbstractUser를 상속받는 모델을 생성
    class User(AbstractUser):
        nickname = models.CharField(max_length=50)
        phone = models.PhoneNumberField(unique = True, null = False, blank = False)
    ㄴ User모델에서 동작은 그대로 하지만, 필드만 재정의하고 싶을 때 사용,
       기존 필드를 사용하면서 새로 정의한 필드를 추가할 때 사용,
       내부에 설정된 필수 필드 자동생성....,
       settings.py에다가 AUTH_USER_MODEL = 'app_name.User'를 추가

3.AbstractBaseUser를 상속받는 모델을 생성 -> 추가로 PermissionsMixin 필수 상속
    - is_active = models.BooleanField(default=True)   # 계정 활성화 여부
    - is_staff = models.BooleanField(default=False)   # 관리자 권한 여부
    - objects = UserManager()
    ㄴ 3개 필수 선언
    class User(AbstractBaseUser):
        id = UUIDField(primary_key=True, max_length=64, unique=True, null=False)
        name = CharField(max_length=255, unique=False)
        email = EmailField(unique=True)
    ㄴ 로그인 방식의 변경, 원하는 필드들로 유저 모델의 구현 등등 완전한 커스터마이징을 하고 싶을 때 사용,
       필수 필드로 password 하나의 필드만 설정
       
       
****  마이그레이션 하면 settings.py의 INSTALLED_APPS = [] 정의된 모든 앱에서 테이블이 생김.......
"""


# Django의 권한 시스템 쓸려면 상속 필수 AbstractUser, (AbstractBaseUser, PermissionsMixin)
class Users(AbstractUser):
    """
    Django 내부적으로는 id 필드를 외래키 참조 대상으로 사용합니다 (예: admin 로그 테이블).
    index를 primary key로 만들면 Django의 기본 흐름과 어긋나서 FK 오류를 유발할 수 있습니다.
    따라서 id는 그대로 두고, index는 필요하면 별도 관리.
    """

    id = models.BigAutoField(
        primary_key=True, verbose_name="인덱스"
    )  # FK가 참조하기 좋은 기본키 (기본적으로 Django가 사용하는 타입)
    email = models.CharField(
        unique=True, max_length=20, null=False, verbose_name="이메일"
    )
    password = models.CharField(max_length=128, null=False, verbose_name="비밀번호")
    user_name = models.CharField(max_length=10, null=False, verbose_name="회원이름")
    position = models.CharField(max_length=20, null=False, verbose_name="직급")
    phone = models.CharField(max_length=15, null=False, verbose_name="핸드폰")
    company = models.CharField(max_length=20, null=False, verbose_name="회사")
    join_date = models.DateTimeField(max_length=20, null=False, verbose_name="가입일")

    # 기본 생성되는 필드 생성 안되게( admin에서 쓰는게 있어 모두 생성 안하면 작동안되는게 있음 - 로그인)
    username = None
    first_name = None
    last_name = None

    USERNAME_FIELD = "email"  # 로그인 시 사용할 필드
    REQUIRED_FIELDS = (
        []
    )  # 필수 설정 AbstractUser를 상속했기 때문에 내부적으로 REQUIRED_FIELDS 가 이미 정의되어 있어 email이 자동 포함되어있음
    objects = (
        CustomUserManager()
    )  # 기본 UserManager는 username을 요구 / 그래서 create_user()를 그대로 못씀 / 오버라이드해서 써야함 (managers.py 생성)

    class Meta:
        db_table = "users"  # 👈 테이블명을 직접 지정
