from django.urls import path
from . import views
from . import receivers

app_name = 'terno'

urlpatterns = [
    path('', views.index, name='index'),
    path('settings', views.settings, name='settings'),
    path('get-sql/', views.get_sql, name='get_sql'),
    path('execute-sql', views.execute_sql, name='execute_sql'),
]
