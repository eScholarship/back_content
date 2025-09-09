import requests

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from security.decorators import editor_user_required

from core.models import Account, Galley
from core.views import BaseUserList

from submission.models import (Article,
                               ArticleAuthorOrder,
                               STAGE_PUBLISHED)
from submission.forms import AuthorForm
from submission.logic import check_author_exists

from production.forms import GalleyForm
from production.logic import (save_galley,
                              get_all_galleys)

from journal.logic import get_galley_content

from plugins.back_content.forms import (ArticleInfo,
                                        PublicationInfo,
                                        DepositAgreementForm,
                                        RemoteParse)
from plugins.back_content.logic import (get_and_parse_doi_metadata,
                                        parse_url_results)

from utils.shared import generate_password


@editor_user_required
def index(request):
    articles = Article.objects.filter(
        journal=request.journal,
    ).exclude(
        stage=STAGE_PUBLISHED
    ).select_related(
        'correspondence_author',
        'section',
    )

    template = 'back_content/index.html'
    context = {
        'articles': articles,
    }

    return render(request, template, context)

@editor_user_required
def create_article(request):
    additional_fields = request.journal.field_set.all()
    if request.method == 'POST':
        article_form = ArticleInfo(request.POST,
                                   additional_fields=additional_fields,
                                   journal=request.journal)
        deposit_form = DepositAgreementForm(request.POST)
        if article_form.is_valid() and deposit_form.is_valid():
            article = article_form.save()
            article.journal = request.journal
            article.owner = request.user
            article.save()
            return redirect(reverse('bc_add_authors', kwargs={"article_id": article.pk}))
    else:
        article_form = ArticleInfo(journal=request.journal,
                                   additional_fields=additional_fields,)
        deposit_form = DepositAgreementForm()

    template = 'back_content/article_form.html'
    context = {
        'article_form': article_form,
        'additional_fields': additional_fields,
        'deposit_form': deposit_form
    }

    return render(request, template, context)

@editor_user_required
def edit_article(request, article_id):
    article = get_object_or_404(
        Article,
        pk=article_id,
        journal=request.journal,
    )

    additional_fields = request.journal.field_set.all()
    if request.method == 'POST':
        article_form = ArticleInfo(request.POST,
                                   additional_fields=additional_fields,
                                   journal=request.journal,
                                   instance=article)
        if article_form.is_valid():
            article = article_form.save(request=request)
            article.journal = request.journal
            article.owner = request.user
            article.save()
            if "save_continue" in request.POST:
                return redirect(reverse('bc_add_authors', kwargs={"article_id": article.pk}))
            else:
                return redirect(reverse('bc_index'))
    else:
        article_form = ArticleInfo(journal=request.journal,
                                   additional_fields=additional_fields,
                                   instance=article)

    template = 'back_content/article_form.html'
    context = {
        'article': article,
        'article_form': article_form,
        'additional_fields': additional_fields,
    }

    return render(request, template, context)

@editor_user_required
def add_authors(request, article_id):
    article = get_object_or_404(
        Article,
        pk=article_id,
        journal=request.journal,
    )

    if request.method == "POST":

        correspondence_author = request.POST.get('main-author', None)

        if correspondence_author:
            author = Account.objects.get(pk=correspondence_author)
            article.correspondence_author = author
            article.save()

        if 'add_author' in request.POST:
            author_form = AuthorForm(request.POST)
            author = check_author_exists(request.POST.get('email'))

            if author:
                article.authors.add(author)
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    '%s added to the article' % author.full_name(),
                )
            else:
                if author_form.is_valid():
                    author = author_form.save(commit=False)
                    author.username = author.email
                    author.set_password(generate_password())
                    author.save()
                    author.add_account_role(
                        role_slug='author',
                        journal=request.journal,
                    )
                    article.authors.add(author)
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        '%s added to the article' % author.full_name(),
                    )

            ArticleAuthorOrder.objects.get_or_create(
                article=article,
                author=author,
                defaults={
                    'order': article.next_author_sort(),
                }
            )
        elif 'remove_author' in request.POST:
            author_pk = request.POST.get('remove_author', None)
            if author_pk:
                author_to_remove = get_object_or_404(
                    Account,
                    pk=author_pk,
                )
                article.authors.remove(author_to_remove)
                ArticleAuthorOrder.objects.filter(
                    article=article,
                    author=author_to_remove,
                ).delete()
                if author_to_remove == article.correspondence_author:
                    article.correspondence_author = None
                    article.save()
                messages.success(
                    request,
                    f'{author_to_remove} removed from article.',
                )
            else:
                messages.warning(
                    request,
                    f'No author ID provided.',
                )
        elif "set_main" in request.POST:
            correspondence_author = request.POST.get('set_main', None)

            if correspondence_author:
                author = Account.objects.get(pk=correspondence_author)
                article.correspondence_author = author
                article.save()
        else:
            if "continue" in request.POST:
                return redirect(reverse('bc_add_galleys', kwargs={"article_id": article.pk}))
            elif "back" in request.POST:
                return redirect(reverse('bc_edit_article', kwargs={"article_id": article.pk}))
            else:
                return redirect(reverse('bc_index'))
    else:
        author_form = AuthorForm()

    context = {
        'article': article,
        'form': author_form,
    }
    return render(request, "back_content/author_form.html", context)


@editor_user_required
def add_galleys(request, article_id):
    article = get_object_or_404(
        Article,
        pk=article_id,
        journal=request.journal,
    )
    galley_form = GalleyForm()
    if request.method == "POST":
        if "file" in request.FILES:
            label = request.POST.get('label')
            for uploaded_file in request.FILES.getlist('file'):
                save_galley(
                    article,
                    request,
                    uploaded_file,
                    is_galley=True,
                    label=label,
                )
        elif "continue" in request.POST:
            return redirect(reverse('bc_publish_article', kwargs={"article_id": article.pk}))
        elif "close" in request.POST:
            return redirect(reverse('bc_index'))
        elif "back" in request.POST:
            return redirect(reverse('bc_add_authors', kwargs={"article_id": article.pk}))

    context = {
        "article": article,
        'galleys': get_all_galleys(article),
        "galley_form": galley_form
    }
    return render(request, "back_content/galley_form.html", context)


@editor_user_required
def publish(request, article_id):
    article = get_object_or_404(
        Article,
        pk=article_id,
        journal=request.journal,
    )

    if request.method == 'POST':
        pub_form = PublicationInfo(request.POST, 
                                   instance=article)
        if pub_form.is_valid():
            article = pub_form.save()
            
            if article.primary_issue:
                article.primary_issue.articles.add(article)
                article.save()

            if 'save_close' in request.POST:
                return redirect('bc_index')
            elif 'publish' in request.POST:
                if not article.stage == STAGE_PUBLISHED:
                    article.stage = STAGE_PUBLISHED
                    article.snapshot_authors(article)
                    article.save()
                return redirect(reverse('manage_archive_article', kwargs={"article_id": article.pk}))
            else:
                return redirect(reverse('bc_create_article'))
    else:
        pub_form = PublicationInfo(instance=article)

    template = 'back_content/publish_form.html'
    context = {
        'pub_form': pub_form,
        'article': article
    }

    return render(request, template, context)

@editor_user_required
def doi_import(request):
    form = RemoteParse()

    if request.POST:
        form = RemoteParse(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            mode = form.cleaned_data['mode']

            if mode == 'doi':
                r = requests.get('https://api.crossref.org/v1/works/{0}'.format(url)).json()
                article = get_and_parse_doi_metadata(r, request, doi=url)
                return redirect(reverse('bc_article', kwargs={'article_id': article.pk}))
            else:
                r = requests.get(url)
                article = parse_url_results(r, request)
                return redirect(reverse('bc_article', kwargs={'article_id': article.pk}))

    template = 'back_content/doi_import.html'
    context = {
        'form': form,
    }

    return render(request, template, context)

@editor_user_required
def preview_xml_galley(request, article_id, galley_id):
    """
    Allows an editor to preview an article's XML galleys.
    :param request: HttpRequest
    :param article_id: Article object ID (INT)
    :param galley_id: Galley object ID (INT)
    :return: HttpResponse
    """

    article = get_object_or_404(Article, journal=request.journal, pk=article_id)
    galley = Galley.objects.filter(article=article, file__mime_type__contains='/xml', pk=galley_id)

    if not galley:
        raise Http404

    content = get_galley_content(article, galley)

    template = 'journal/article.html'
    context = {
        'article': article,
        'galleys': galley,
        'article_content': content
    }

    return render(request, template, context)

class BCPAuthorSearch(BaseUserList):

    model = Account
    template_name = 'back_content/author_search.html'

    def dispatch(self, request, *args, **kwargs):
        self.article = get_object_or_404(
            Article,
            pk=kwargs.get('article_id'),
            journal=request.journal,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_facets(self):
        facets = {
            'q': {
                'type': 'search',
                'field_label': 'Search',
            },
            'is_active': {
                'type': 'boolean',
                'field_label': 'Active status',
                'true_label': 'Active',
                'false_label': 'Inactive',
            },
        }
        return self.filter_facets_if_journal(facets)

    def get_order_by_choices(self):
        return [
            ('last_name', _('Last name A-Z')),
            ('-last_name', _('Last name Z-A')),
            ('-date_joined', _('Newest')),
            ('date_joined', _('Oldest')),
        ]

    def get_queryset(self, params_querydict=None):
        return super().get_queryset().exclude(
            pk__in=self.article.authors.all().values_list(
                'pk',
                flat=True,
            ),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['article'] = self.article
        return context

    def post(self, request, *args, **kwargs):
        if "add_author" in request.POST:
            author_id = request.POST.get("add_author")
            author = get_object_or_404(
                Account,
                pk=author_id,
            )
            if author in self.get_queryset():
                self.article.authors.add(author)
                ArticleAuthorOrder.objects.get_or_create(
                    article=self.article,
                    author=author,
                    defaults={
                        'order': self.article.next_author_sort(),
                    }
                )
                messages.success(
                    request,
                    f"{author} has been added as an author.",
                )

        # No role management, so call the grandparent's post.
        return super(BaseUserList, self).post(request, *args, **kwargs)