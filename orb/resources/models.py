"""
Models for resources, primarily content (resource) review releated models.

The core model is the ContentReview model, which is used for both content
review assignment and review itself. It's built around the ReviewCompetency
model which is used to model the competency role which a reviewer has.

In the initial modeling a resource should have three reviews, one for each of
the three initial roles. These are built around database models and uniquness
constraints rather than with selections or with multiple foreign keys for
deployable flexibility. This still provides a constraint, enabling assignment
across all review roles and allowing the enforcement of this, but without
dictating what the role names are or how many should be used.

The ContentReview model makes uses of Django Finite State Machine to provide
an interface for managing the state of the review as well as associated
side effects of changing the status.
"""

from django.conf import settings
from django.db import models
from django_fsm import FSMField, transition

from orb.models import TimestampBase, Resource, ReviewerRole


class ContentReview(TimestampBase):
    """
    Model class used to assign a content review for a resource to
    a content reviewer and to capture the review result.
    """
    resource = models.ForeignKey('orb.Resource', related_name="content_reviews")
    status = FSMField(default=Resource.PENDING)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL)
    notes = models.TextField(blank=True)
    role = models.ForeignKey(ReviewerRole, related_name="reviews")

    class Meta:
        unique_together = (
            ('resource', 'reviewer'),
            ('resource', 'role'),
        )

    @transition(field=status, source=Resource.PENDING, target=Resource.APPROVED)
    def approve(self):
        return None

    @transition(field=status, source=Resource.PENDING, target=Resource.REJECTED)
    def reject(self):
        return None


class ReviewLogEntry(TimestampBase):
    """
    Model class used to track individual actions made with regard
    to a resource's content review.

    """
    review = models.ForeignKey(ContentReview, related_name="log_entries")
    review_status = models.CharField(editable=False, max_length=20)
    action = models.CharField(max_length=200)

