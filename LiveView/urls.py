from django.urls import path, include

from . import views


app_name = 'LiveView'
urlpatterns = [
    path('', views.index, name='index'),
    path('startAdmin', views.startAdmin, name='startAdmin'),
    path('start', views.start, name='start'),
    path('stream', views.stream, name='stream'),
    path('stop', views.stop, name='stop'),
    path('stopAdmin', views.stopAdmin, name='stopAdmin'),
    path('openAdmin', views.openAdmin, name='openAdmin'),
    path('open', views.open, name='open'),
    path('takeSnap', views.takeSnapshot, name='takeSnap')
]
