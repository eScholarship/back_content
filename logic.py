import datetime
import uuid
from bs4 import BeautifulSoup

from django.contrib import messages
from django.shortcuts import reverse, redirect

from submission import models
from identifiers import models as ident_models
from core import models as core_models


def parse_url_results(r, request):
    soup = BeautifulSoup(r.text, 'lxml')

    title = soup.find('meta', {'name': "citation_title"}).get('content', '')
    pub_date = soup.find('meta', {'name': "citation_date"}).get('content', '')
    doi = soup.find('meta', {'name': "citation_doi"}).get('content', None)
    lang = soup.find('meta', {'name': "citation_language"}).get('content', '')
    abstract = soup.find('meta', {'name': "description"}).get('content', '')

    article = models.Article.objects.create(
        title=title,
        date_published=pub_date,
        language=lang,
        abstract=abstract,
        is_remote=True,
        remote_url=r.url,
        journal=request.journal
    )

    if doi:
        identifier = ident_models.Identifier.objects.create(
            id_type='doi',
            identifier=doi,
            enabled=True,
            article=article
        )

        id_message = 'Identifier {0} created.'.format(identifier)
        messages.add_message(request, messages.SUCCESS, id_message)

    messages.add_message(request, messages.SUCCESS, 'Article created.')
    return article


def get_and_parse_doi_metadata(r, request, doi):
    message = r.get('message')

    title = message.get('title', '')[0]
    date_parts = message.get('published-online').get("date-parts")[0]
    pub_date = datetime.datetime(year=date_parts[0], month=date_parts[1], day=date_parts[2])
    doi = doi
    abstract = message.get('abstract', '')

    article = models.Article.objects.create(
        title=title,
        date_published=pub_date,
        abstract=abstract,
        is_remote=True,
        remote_url='https://doi.org/{0}'.format(doi),
        journal=request.journal
    )

    if doi:
        identifier = ident_models.Identifier.objects.create(
            id_type='doi',
            identifier=doi,
            enabled=True,
            article=article
        )

        id_message = 'Identifier {0} created.'.format(identifier)
        messages.add_message(request, messages.SUCCESS, id_message)

    for author in message.get('author', None):
        affiliation = author['affiliation'][0].get('name', '') if len(author['affiliation']) > 0 else ""
        new_author = core_models.Account.objects.create(
            email="{0}@journal.com".format(uuid.uuid4()),
            first_name=author.get('given', ''),
            last_name=author.get('family', ''),
            institution=affiliation,
        )
        article.authors.add(new_author)

    messages.add_message(request, messages.SUCCESS, 'Article created.')
    return article


def return_url(article, section=None):
    url = reverse(
        'bc_article',
        kwargs={
            'article_id': article.pk,
        },
    )
    if section:
        return redirect(f"{url}#{section}")
    return redirect(url)
