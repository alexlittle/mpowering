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
from django_fsm import FSMField, transition, TransitionNotAllowed
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from orb.models import TimestampBase, Resource, ReviewerRole
from orb.review import signals


class ReviewLogEntry(TimestampBase):
    """
    Model class used to track individual actions made with regard
    to a resource's content review.

    """
    review = models.ForeignKey('ContentReview', related_name="log_entries")
    review_status = models.CharField(editable=False, max_length=20)
    action = models.CharField(max_length=200)

    class Meta:
        verbose_name = _("review log entry")
        verbose_name_plural = _("review log entries")

    def __unicode__(self):
        return u"{0}: {1}".format(self.review, self.review_status)


class ReviewQueryset(models.QuerySet):

    def pending(self):
        return self.filter(status=Resource.PENDING)

    def complete(self):
        return self.exclude(status=Resource.PENDING)

    def for_user(self, user):
        return self.filter(reviewer=user)

    def assign(self, assigned_by=None, **kwargs):
        """
        Extended alias of `create` to create new review and log
        assignment in one step.

        Args:
            assigned_by: a User instance
            **kwargs: QuerySet.create ready kwargs

        Returns:
            a new model instance

        """
        review = self.create(**kwargs)
        signals.review_assigned.send(review.__class__, review,
                                     assigned_by=assigned_by or review.reviewer)
        return review


class ContentReview(TimestampBase):
    """
    Model class used to assign a content review for a resource to
    a content reviewer and to capture the review result.
    """
    resource = models.ForeignKey('orb.Resource', related_name="content_reviews")
    status = FSMField(default=Resource.PENDING)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL)
    notes = models.TextField(blank=True)
    criteria = models.ManyToManyField('orb.ResourceCriteria', blank=True)
    role = models.ForeignKey(ReviewerRole, related_name="reviews")

    reviews = ReviewQueryset.as_manager()
    objects = reviews

    class Meta:
        verbose_name = _("content review")
        verbose_name_plural = _("content reviews")
        unique_together = (
            ('resource', 'reviewer'),
            ('resource', 'role'),
        )

    def __unicode__(self):
        return u"{0}: {1}".format(self.reviewer, self.resource)

    @transition(field=status, source=Resource.PENDING, target=Resource.APPROVED)
    def approve(self):
        signals.review_approved.send(self.__class__, review=self)
        return None

    @transition(field=status, source=Resource.PENDING, target=Resource.REJECTED)
    def reject(self):
        signals.review_rejected.send(self.__class__, review=self)
        return None

    @property
    def is_pending(self):
        return self.status == Resource.PENDING

    def reassign(self, new_user):
        """

        Args:
            new_user:

        Returns:

        """
        if new_user == self.reviewer:
            return None

        if self.status != Resource.PENDING:
            raise TransitionNotAllowed("Cannot reassign a completed review")
        
        old_reviewer = self.reviewer
        self.reviewer = new_user
        # TODO send email
        ReviewLogEntry.objects.create(
            review=self,
            review_status=self.status,
            action="Reassigned from {0} to {1}".format(old_reviewer, new_user),
        )


def process_resource_reviews(resource):
    """
    Checks on the status of a resource's reviews and possibly updates
    the status of that resource based on the reviews.

    If *all* roles have been assigned content reviews and *all* reviews
    are approved, then the resource is approved.

    If *all* roles have been assigned content reviews and *all* have been
    reviewed and *at least one* is rejected, the resource is rejected.

    Otherwise no action is taken.

    Args:
        resource: a Resource instance

    Returns:
        the resource status

    """
    roles_count = ReviewerRole.roles.all().count()
    reviews_count = resource.content_reviews.all().count()
    if roles_count != reviews_count:
        return resource.status

    review_status = set(resource.content_reviews.all().values_list('status', flat=True))

    if review_status == {Resource.APPROVED}:
        resource.approve()
        resource.save()
        signals.resource_approved.send(sender=resource.__class__, resource=resource)
        return resource.status
    if Resource.PENDING not in review_status:
        resource.reject()
        resource.save()
        signals.resource_rejected.send(sender=resource.__class__, resource=resource)
        return resource.status

    return resource.status


@receiver(signals.review_assigned)
def review_assigned(sender, review, assigned_by, **kwargs):
    """
    Handles the behavior after a review is assigned

    Args:
        review: the assigned review
        assigned_by: user who initiated assignment

    Returns:
        None

    """
    ReviewLogEntry.objects.create(
        review=sender,
        review_status=review.status,
        action="Assigned to {0} by {1}".format(review.reviewer, assigned_by),
    )


@receiver(signals.review_rejected)
def review_rejected(sender, review, **kwargs):
    """
    Handles the behavior after a resource is rejected by a reviewer

    Args:
        sender: sending class
        review: the assigned review

    Returns:
        None

    """
    ReviewLogEntry.objects.create(
        review=review,
        review_status=review.status,
        action="Rejected by {0}".format(review.reviewer),
    )
    process_resource_reviews(review.resource)


@receiver(signals.review_approved)
def review_approved(sender, review, **kwargs):
    """
    Handles the behavior after a resource is approved by a reviewer

    Args:
        sender: sending class
        review: the assigned review

    Returns:
        None

    """
    ReviewLogEntry.objects.create(
        review=review,
        review_status=review.status,
        action="Approved by {0}".format(review.reviewer),
    )
    process_resource_reviews(review.resource)


@receiver(signals.resource_rejected)
def resource_rejected(sender, resource, **kwargs):
    """
    Handles actions after a resource has been finally rejected

    Args:
        sender: sending class
        resource: rejected resource

    Returns:

    """
    # TODO send email


@receiver(signals.resource_approved)
def resource_approved(sender, resource, **kwargs):
    """
    Handles actions after a resource has been finally approved

    Args:
        sender: sending class
        resource: approved resource

    Returns:

    """
    # TODO send email
