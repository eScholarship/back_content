from bs4 import BeautifulSoup

from django.contrib import messages

from submission import models
from identifiers import models as ident_models


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


def get_and_parse_doi_metadata(url, request):
    crossref_quert = request.get