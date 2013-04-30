import os
from datetime import datetime
import requests
import bs4
import json

from django.db import models
from django.conf import settings
from django.utils import timezone

from screamshot.utils import casperjs_capture

from caminae.common.utils import smart_urljoin
from caminae.paperclip.models import Attachment


# Used to create the matching url name
ENTITY_LAYER = "layer"
ENTITY_LIST = "list"
ENTITY_JSON_LIST = "json_list"
ENTITY_FORMAT_LIST = "format_list"
ENTITY_DETAIL = "detail"
ENTITY_MAPIMAGE = "mapimage"
ENTITY_DOCUMENT = "document"
ENTITY_CREATE = "add"
ENTITY_UPDATE = "update"
ENTITY_DELETE = "delete"

ENTITY_KINDS = (
    ENTITY_LAYER, ENTITY_LIST, ENTITY_JSON_LIST,
    ENTITY_FORMAT_LIST, ENTITY_DETAIL, ENTITY_MAPIMAGE, ENTITY_DOCUMENT, ENTITY_CREATE,
    ENTITY_UPDATE, ENTITY_DELETE,
)


class MapImageError(Exception):
    pass


class MapEntityMixin(object):

    @classmethod
    def add_property(cls, name, func):
        if hasattr(cls, name):
            return  # ignore
        setattr(cls, name, property(func))

    @classmethod
    def latest_updated(cls):
        try:
            return cls.objects.latest("date_update").date_update
        except cls.DoesNotExist:
            return None

    # List all different kind of views
    @classmethod
    def get_url_name(cls, kind):
        if not kind in ENTITY_KINDS:
            return None
        return '%s:%s_%s' % (cls._meta.app_label, cls._meta.module_name, kind)

    @classmethod
    def get_url_name_for_registration(cls, kind):
        if not kind in ENTITY_KINDS:
            return None
        return '%s_%s' % (cls._meta.module_name, kind)

    @classmethod
    @models.permalink
    def get_layer_url(cls):
        return (cls.get_url_name(ENTITY_LAYER), )

    @classmethod
    @models.permalink
    def get_list_url(cls):
        return (cls.get_url_name(ENTITY_LIST), )

    @classmethod
    @models.permalink
    def get_jsonlist_url(cls):
        return (cls.get_url_name(ENTITY_JSON_LIST), )

    @classmethod
    @models.permalink
    def get_format_list_url(cls):
        return (cls.get_url_name(ENTITY_FORMAT_LIST), )

    @classmethod
    @models.permalink
    def get_add_url(cls):
        return (cls.get_url_name(ENTITY_CREATE), )

    def get_absolute_url(self):
        return self.get_detail_url()

    @classmethod
    @models.permalink
    def get_generic_detail_url(cls):
        return (cls.get_url_name(ENTITY_DETAIL), [str(0)])

    @models.permalink
    def get_detail_url(self):
        return (self.get_url_name(ENTITY_DETAIL), [str(self.pk)])

    @property
    def attachments(self):
        return Attachment.objects.attachments_for_object(self)

    def prepare_map_image(self, rooturl):
        path = self.get_map_image_path()
        # If already exists and up-to-date, do nothing
        if os.path.exists(path):
            if os.path.getsize(path) > 0:
                modified = datetime.fromtimestamp(os.path.getmtime(path))
                modified = modified.replace(tzinfo=timezone.utc)
                if modified > self.date_update:
                    return
            else:
                os.remove(path)
        # Run head-less capture (takes time)
        url = smart_urljoin(rooturl, self.get_detail_url())
        printcontext = dict(mapsize=dict(width=800, height=600))
        printcontext['print'] = True
        url += '?context=' + json.dumps(printcontext)
        with open(path, 'wb') as f:
            casperjs_capture(f, url, selector='.map-panel')
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise MapImageError("%s could not be captured into %s" % (url, path))
        # TODO : remove capture image file on delete

    def get_map_image_path(self):
        basefolder = os.path.join(settings.MEDIA_ROOT, 'maps')
        if not os.path.exists(basefolder):
            os.mkdir(basefolder)
        return os.path.join(basefolder, '%s-%s.png' % (self._meta.module_name, self.pk))

    @property
    def map_image_url(self):
        return self.get_map_image_url()

    @models.permalink
    def get_map_image_url(self):
        return (self.get_url_name(ENTITY_MAPIMAGE), [str(self.pk)])

    @models.permalink
    def get_document_url(self):
        return (self.get_url_name(ENTITY_DOCUMENT), [str(self.pk)])

    @models.permalink
    def get_update_url(self):
        return (self.get_url_name(ENTITY_UPDATE), [str(self.pk)])

    @models.permalink
    def get_delete_url(self):
        return (self.get_url_name(ENTITY_DELETE), [str(self.pk)])

    def get_attributes_html(self, rooturl):
        """
        The tidy XHTML version of objects attributes.

        Since we have to insert them in document exports, we extract the
        ``details-panel`` of the detail page, using BeautifulSoup.
        With this, we save a lot of efforts, since we do have to build specific Appy.pod
        templates for each model.
        """
        if getattr(settings, 'TEST', False):
            return '<p>Mock</p>'  # TODO: better run in LiveServerTestCase instead !

        url = smart_urljoin(rooturl, self.get_detail_url())
        r = requests.get(url)
        if r.status_code != 200:
            raise ValueError('Could not reach %s' % url)

        soup = bs4.BeautifulSoup(r.content)
        details = soup.find(id="properties")
        if details is None:
            raise ValueError('Content is of detail page is invalid')

        # Remove "Add" buttons
        for p in details('p'):
            if 'autohide' in p.get('class', ''):
                p.extract()
        # Remove Javascript
        for s in details('script'):
            s.extract()
        # Remove images (Appy.pod fails with them)
        for i in details('img'):
            i.replaceWith(i.get('title', ''))
        # Remove links (Appy.pod sometimes shows empty strings)
        for a in details('a'):
            a.replaceWith(a.text)
        # Prettify (ODT compat.) and convert unicode to XML entities
        cooked = details.prettify('ascii', formatter='html')
        return cooked
