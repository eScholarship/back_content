from django.conf.urls import url

from plugins.back_content import views

urlpatterns = [
    url(r'^$', views.index, name='bc_index'),
    url(r'^article/(?P<article_id>\d+)/$', views.article, name='bc_article'),

    url(r'^xml_import/$', views.xml_import_upload, name='bc_xml_import_upload'),
    url(r'^xml_import/(?P<filename>[\w.-]{0,256})$', views.xml_import_parse, name='bc_xml_import_parse'),
]
