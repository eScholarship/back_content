from django.urls import re_path

from plugins.back_content import views

from journal.views import article_figure

urlpatterns = [
    re_path(r'^$', views.index, name='bc_index'),
    re_path(r'^article/(?P<article_id>\d+)/$', views.article, name='bc_article'),

    re_path(r'^xml_import/$', views.xml_import_upload, name='bc_xml_import_upload'),
    re_path(r'^xml_import/(?P<filename>[\w.-]{0,256})$', views.xml_import_parse, name='bc_xml_import_parse'),

    re_path(r'^doi_import/$', views.doi_import, name='bc_doi_import'),

    re_path(r'^article/(?P<article_id>\d+)/galley/(?P<galley_id>\d+)/$', views.preview_xml_galley,
        name='bc_preview_xml_galley'),

    re_path(r'^article/(?P<article_id>\d+)/galley/(?P<galley_id>\d+)/figures/(?P<file_name>.*)/$',
        article_figure,
        name='bc_article_figure',
    ),
    re_path(
        r'^article/(?P<article_id>\d+)/authors/$',
        views.BCPAuthorSearch.as_view(),
        name='bc_article_authors',
    ),
]
