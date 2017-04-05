# orb/context_processors.py
from datetime import date
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
import orb
from orb.models import Category, Tag, TagOwner


def get_menu(request):
    topics = Tag.tags.public().top_level()
    
    if request.user.is_authenticated():
        tags = TagOwner.objects.filter(user=request.user)
    else:
        tags = None

    if request.user.is_authenticated():
        if request.user.userprofile and request.user.userprofile.is_reviewer:
            reviewer = True
        else:
            reviewer = False
    else:
        reviewer = False
    
    return {
        'header_menu_categories': topics,
        'header_owns_tags': tags,
        'settings': settings,
        'reviewer': reviewer,
        
    }


def get_version(request):
    version = "v" + str(orb.VERSION[0]) + "." + \
        str(orb.VERSION[1]) + "." + str(orb.VERSION[2])

    if getattr(settings, 'STAGING', False):
        staging = True
    else:
        staging = False

    notices = []
    #if date.today() >= date(2017, 04, 05) and date.today() <= date(2017, 04, 30):
    #    notices.append(_(u'<strong>ORB Survey.</strong> We\'re looking for your feedback on ORB, take our survey now... '))
        
    return {'version': version,
            'ORB_GOOGLE_ANALYTICS_CODE': settings.ORB_GOOGLE_ANALYTICS_CODE,
            'ORB_RESOURCE_MIN_RATINGS': settings.ORB_RESOURCE_MIN_RATINGS,
            'STAGING': staging,
            'NOTICES': notices,}


def base_context_processor(request):
    return {
        'BASE_URL': request.build_absolute_uri("/").rstrip("/")
    }
