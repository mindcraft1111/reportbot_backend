from django.urls import path

from .junds.junds import gemini_streaming_junds
from .kakaka9509.kakaka9509 import gemini_streaming_kakaka9509
from .mjylove26.mjylove26 import gemini_streaming_mjylove26
from .tjrgh.tjrgh import gemini_streaming_tjrgh
from .udyujin.udyujin import gemini_streaming_udyujin

urlpatterns = [
    path("junds/", gemini_streaming_junds),
    path("kakaka9509/", gemini_streaming_kakaka9509),
    path("mjylove26/", gemini_streaming_mjylove26),
    path("tjrgh/", gemini_streaming_tjrgh),
    path("udyujin/", gemini_streaming_udyujin),
]
