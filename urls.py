from django.conf.urls import url

from plugins.back_content import views

urlpatterns = [
    url(r'^$', views.index, name='bc_index'),
    url(r'^article/(?P<article_id>\d+)/$', views.article, name='bc_article')
]