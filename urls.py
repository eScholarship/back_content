from django.urls import re_path

from plugins.back_content import views

from journal.views import article_figure

urlpatterns = [
    re_path(r'^$', views.index, name='bc_index'),
    re_path(r'^article/create/$', views.create_article, name='bc_create_article'),
    re_path(r'^article/(?P<article_id>\d+)/edit/$', views.edit_article, name='bc_edit_article'),
    re_path(r'^article/(?P<article_id>\d+)/authors/$', views.add_authors, name='bc_add_authors'),
    re_path(r'^article/(?P<article_id>\d+)/galleys/$', views.add_galleys, name='bc_add_galleys'),
    re_path(r'^article/(?P<article_id>\d+)/publish/$', views.publish, name='bc_publish_article'),

    re_path(r'^doi_import/$', views.doi_import, name='bc_doi_import'),

    re_path(r'^article/(?P<article_id>\d+)/galley/(?P<galley_id>\d+)/$', views.preview_xml_galley,
        name='bc_preview_xml_galley'),

    re_path(r'^article/(?P<article_id>\d+)/galley/(?P<galley_id>\d+)/figures/(?P<file_name>.*)/$',
        article_figure,
        name='bc_article_figure',
    ),
    re_path(
        r'^article/(?P<article_id>\d+)/add_author/$',
        views.BCPAuthorSearch.as_view(),
        name='bc_article_authors',
    ),
]
