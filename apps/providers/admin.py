from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.providers.models import ProviderVerification, TutorDetail, TutorSubject, StatusChoices
from apps.providers.services import apply_verification_outcome

_MUTABLE_FOR_APPROVE = {StatusChoices.PENDING, StatusChoices.REJECTED}
_MUTABLE_FOR_REJECT = {
    StatusChoices.PENDING,
    StatusChoices.APPROVED
}

@action(
    description = _("Approve provider verification request PENDING -> APPROVED"),
    icon="check_circle",
)
def approve_provider_request(modeladmin, request, queryset):
    eligible = queryset.filter(status__in=_MUTABLE_FOR_APPROVE)
    skipped = queryset.exclude(status__in=_MUTABLE_FOR_APPROVE).count()

    approved = 0
    for verification in eligible:
        verification.status = StatusChoices.APPROVED
        verification.comment = ""
        verification.save(update_fields=["status", "comment", "updated_at"])
        apply_verification_outcome(verification, request.user)
        approved += 1

    if approved: 
        modeladmin.message_user(
            request,
            _("%(n)d verification(s) APPROVED.") % {"n": approved},
            messages.SUCCESS,
        )
    
    if skipped:
        modeladmin.message_user(
            request,
            _("%(n)d only PENDING or REJECTED verifications are eligible for APPROVE")
            % {"n": skipped},
            messages.WARNING,
        ) 
        
        

@action(
    description = _("Reject provider verification request"),
    icon="cancel",
)
def reject_provider_request(modeladmin, request, queryset):
    eligible = queryset.filter(status__in=_MUTABLE_FOR_REJECT)
    skipped = queryset.exclude(status__in=_MUTABLE_FOR_REJECT).count()
    
    rejected = 0
    for verification in eligible:
        verification.status = StatusChoices.REJECTED
        verification.comment = ""
        verification.save(update_fields=["status", "comment", "updated_at"])
        apply_verification_outcome(verification, request.user)
        rejected += 1


    if rejected:
        modeladmin.message_user(
            request,
            _("%(n)d verification(s) rejected.") % {"n": rejected},
            messages.SUCCESS,
        )
    if skipped:
        modeladmin.message_user(
            request,
            _("%(n)d verification(s) was already REJECTED")
            % {"n": skipped},
            messages.WARNING,
        )


@admin.register(TutorDetail)
class TutorDetailAdmin(ModelAdmin):
    list_display = (
        "user_email",
        "user_full_name",
        "is_verified",
        "rating",
        "review_count",
        "price_per_hour_qar",
        "trial_available",
    )
    list_filter = ("is_verified", "trial_available", "languages")
    search_fields = ("user__email", "user__full_name", "credentials", "bio")
    readonly_fields = ("user", "created_at", "updated_at")

    @admin.display(description=_("Email"), ordering="user__email")
    def user_email(self, obj: TutorDetail) -> str:
        return obj.user.email

    @admin.display(description=_("Name"), ordering="user__full_name")
    def user_full_name(self, obj: TutorDetail) -> str:
        return obj.user.full_name


@admin.register(TutorSubject)
class TutorSubjectAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(ProviderVerification)
class ProviderVerificationAdmin(ModelAdmin):
    actions = [reject_provider_request, approve_provider_request]
    
    list_display = (
        "user_email",
        "provider_type",
        "status",
        "updated_at",
    )
    list_filter = ("status", "provider_type")
    search_fields = ("user__email", "user__full_name", "comment")
    readonly_fields = ("user", "provider_type", "created_at", "updated_at")

    @admin.display(description=_("Email"), ordering="user__email")
    def user_email(self, obj: ProviderVerification) -> str:
        return obj.user.email
    
    @display(
        description=_("Status"),
        ordering="status",
        label={
            StatusChoices.APPROVED: "success",
            StatusChoices.PENDING: "warning",
            StatusChoices.CANCELLED: "info",
            StatusChoices.REJECTED: "danger",
        },
    )
    def status_badge(self, obj: ProviderVerification):
        return obj.status, obj.get_status_display()