from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse
from django.contrib import messages

from submission import models, forms, logic
from core import models as core_models, files
from plugins.back_content import forms as bc_forms
from production import logic as prod_logic
from identifiers import logic as id_logic
from security.decorators import editor_user_required
from utils import shared


@editor_user_required
def index(request):
    if request.POST:
        article = models.Article.objects.create(journal=request.journal)
        return redirect(reverse('bc_article', kwargs={'article_id': article.pk}))

    template = 'back_content/new_article.html'
    context = {}

    return render(request, template, context)

@editor_user_required
def article(request, article_id):
    article = get_object_or_404(models.Article, pk=article_id, journal=request.journal)
    article_form = forms.ArticleInfo(instance=article)
    author_form = forms.AuthorForm()
    pub_form = bc_forms.PublicationInfo(instance=article)
    modal = None

    if request.POST:
        if 'save_section_1' in request.POST:
            article_form = forms.ArticleInfo(request.POST, instance=article)

            if article_form.is_valid():
                article_form.save()
                return redirect(reverse('bc_article', kwargs={'article_id': article.pk}))

        if 'save_section_2' in request.POST:
            correspondence_author = request.POST.get('main-author', None)

            if correspondence_author:
                author = core_models.Account.objects.get(pk=correspondence_author)
                article.correspondence_author = author
                article.save()
                return redirect(reverse('bc_article', kwargs={'article_id': article.pk}))

        if 'save_section_3' in request.POST:
            pub_form = bc_forms.PublicationInfo(request.POST, instance=article)

            if pub_form.is_valid():
                pub_form.save()
                if article.primary_issue:
                    article.primary_issue.articles.add(article)
                return redirect(reverse('bc_article', kwargs={'article_id': article.pk}))

        if 'xml' in request.POST:
            for uploaded_file in request.FILES.getlist('xml-file'):
                prod_logic.save_galley(article, request, uploaded_file, True, "XML", False)

        if 'pdf' in request.POST:
            for uploaded_file in request.FILES.getlist('pdf-file'):
                prod_logic.save_galley(article, request, uploaded_file, True, "PDF", False)

        if 'other' in request.POST:
            for uploaded_file in request.FILES.getlist('other-file'):
                prod_logic.save_galley(article, request, uploaded_file, True, "Other", True)

        if 'add_author' in request.POST:
            form = forms.AuthorForm(request.POST)
            modal = 'author'

            author_exists = logic.check_author_exists(request.POST.get('email'))
            if author_exists:
                article.authors.add(author_exists)
                messages.add_message(request, messages.SUCCESS, '%s added to the article' % author_exists.full_name())
                return redirect(reverse('bc_article', kwargs={'article_id': article_id}))
            else:
                if form.is_valid():
                    new_author = form.save(commit=False)
                    new_author.username = new_author.email
                    new_author.set_password(shared.generate_password())
                    new_author.save()
                    new_author.add_account_role(role_slug='author', journal=request.journal)
                    article.authors.add(new_author)
                    messages.add_message(request, messages.SUCCESS, '%s added to the article' % new_author.full_name())

                    return redirect(reverse('bc_article', kwargs={'article_id': article_id}))

        if 'publish' in request.POST:
            if not article.stage == models.STAGE_PUBLISHED:
                id_logic.generate_crossref_doi_with_pattern(article)
                article.stage = models.STAGE_PUBLISHED
                article.snapshot_authors(article)
                article.save()

            return redirect(reverse('bc_index'))

    template = 'back_content/article.html'
    context = {
        'article': article,
        'article_form': article_form,
        'form': author_form,
        'pub_form': pub_form,
        'galleys': prod_logic.get_all_galleys(article),
        'modal': modal
    }

    return render(request, template, context)


@editor_user_required
def xml_import_upload(request):
    if request.POST and request.FILES:
        xml_file = request.FILES.get('xml_file')
        filename, path = files.save_file_to_temp(xml_file)
        return redirect(reverse('bc_xml_import_parse', kwargs={'filename': filename}))

    template = 'back_content/xml_import.html'
    context = {}

    return render(request, template, context)


@editor_user_required
def xml_import_parse(request, filename):
    path = files.get_temp_file_path_from_name(filename)

    article = logic.import_from_jats_xml(path, request.journal)
    return redirect(reverse('bc_article', kwargs={'article_id': article.pk}))
