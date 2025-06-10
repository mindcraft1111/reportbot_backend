from django.urls import path
from .views import RegisterView, LogoutView, LoginView, DeleteUserView, UpdateUserView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'), 
    path('logout/', LogoutView.as_view(), name='token_logout'), 
    path('login/', LoginView.as_view(), name='token_obtain_pair'), 
    path('del/', DeleteUserView.as_view(), name='delete-account'),
    path('update/', UpdateUserView.as_view(), name='update-account'),
]
