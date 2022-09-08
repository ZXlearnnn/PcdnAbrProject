from django.urls import path
from . import views

app_name = 'RequestProcesser'
urlpatterns=[
        path('Test',views.Test),
        path('TestRedirect/<video_name>',views.TestRedirect),
        path('<video_name>/video/x265/<track>/seg-<segment_id>.mp4',views.ContentRedirect73,name='Content73'),
        path('<video_name>/test1_video/x265/<track>/seg-<segment_id>.mp4',views.test1)
]
