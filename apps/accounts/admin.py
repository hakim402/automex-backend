"""
apps/accounts/admin.py
───────────────────────
Enterprise-grade Unfold admin registration for all accounts models.

Features used from Unfold:
  - Colored status badges                (@display(label=...))
  - Two-line "header" cells w/ initials   (@display(header=True))
  - Boolean check/x icons                 (@display(boolean=True))
  - Tabbed change forms                   (fieldsets classes=["tab"])
  - Tabbed inlines                        (tab = True)
  - Bulk actions                          (@admin.action)
  - Per-row quick actions                 (actions_row / @action)
  - Advanced filters                      (unfold.contrib.filters)
  - Proper password field handling for a custom AbstractBaseUser model
"""

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import action, display

from .models import (
    EmailVerificationToken,
    MagicLinkToken,
    PasswordResetToken,
    Permission,
    Role,
    Tenant,
    User,
    UserMFA,
    UserProfile,
    UserRefreshToken,
    UserRoleAssignment,
)

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────


def _initials(text: str, fallback: str = "?") -> str:
    """Build 1-2 letter initials for header/avatar-style display cells."""
    if not text:
        return fallback
    parts = [p for p in text.strip().split() if p]
    if not parts:
        return fallback
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


# ──────────────────────────────────────────────────────────────────────────────
# CUSTOM USER FORMS
# (User is AbstractBaseUser only — no PermissionsMixin/UsernameField, so we
#  can't reuse django.contrib.auth's UserAdmin/forms as-is. These replicate
#  the safe password-hash behaviour for our custom model.)
# ──────────────────────────────────────────────────────────────────────────────


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password, but you can change the password using the "
            '<a href="../password/">change password form</a>.'
        ),
    )

    class Meta:
        model = User
        fields = "__all__"

    def clean_password(self):
        # Password field is never edited from this form — always return
        # the original hash so it's not accidentally overwritten.
        return self.initial.get("password")


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_("Password confirmation"), widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "role", "tenant")

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError(_("The two password fields didn't match."))
        return p2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# ──────────────────────────────────────────────────────────────────────────────
# INLINES
# ──────────────────────────────────────────────────────────────────────────────


class UserProfileInline(TabularInline):
    model = UserProfile
    extra = 0
    can_delete = False
    tab = True
    verbose_name_plural = _("Profile")
    fields = [
        "phone_number",
        "date_of_birth",
        "city",
        "country",
        "timezone",
        "language",
    ]


class UserRoleAssignmentInline(TabularInline):
    model = UserRoleAssignment
    fk_name = "user"
    extra = 0
    tab = True
    fields = ["role", "assigned_at", "expires_at", "assigned_by"]
    readonly_fields = ["assigned_at"]
    autocomplete_fields = ["role", "assigned_by"]


class UserRefreshTokenInline(TabularInline):
    model = UserRefreshToken
    extra = 0
    can_delete = False
    tab = True
    readonly_fields = [
        "jti",
        "device_name",
        "ip_address",
        "revoked",
        "last_used_at",
        "created_at",
        "expires_at",
    ]
    max_num = 10

    def has_add_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────────────────────────────────────
# TENANT
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(Tenant)
class TenantAdmin(ModelAdmin):
    list_display = ["display_header", "display_tier", "display_active", "user_count", "created_at"]
    list_filter = [
        ("subscription_tier", ChoicesDropdownFilter),
        "is_active",
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]
    list_filter_submit = True
    list_fullwidth = False
    compressed_fields = True
    warn_unsaved_form = True
    save_on_top = True
    list_per_page = 25
    actions = ["activate_tenants", "deactivate_tenants"]

    fieldsets = (
        (
            _("Identity"),
            {"fields": ("id", "name", "slug"), "classes": ["tab"],
             "description": _("Unique tenant identifier and URL slug used for multi-tenant routing.")},
        ),
        (
            _("Subscription"),
            {"fields": ("subscription_tier", "is_active", "settings"), "classes": ["tab"],
             "description": _(
                 "Subscription tier controls feature access across the tenant. "
                 "Settings holds JSON configuration specific to this tenant (branding, limits, etc.). "
                 "Inactive tenants prevent all member logins."
             )},
        ),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_user_count=Count("users"))

    @display(description=_("Tenant"), header=True)
    def display_header(self, obj):
        return [obj.name, obj.slug, _initials(obj.name)]

    @display(
        description=_("Tier"),
        ordering="subscription_tier",
        label={
            Tenant.SubscriptionTier.FREE: "info",
            Tenant.SubscriptionTier.PRO: "warning",
            Tenant.SubscriptionTier.ENTERPRISE: "success",
        },
    )
    def display_tier(self, obj):
        return obj.subscription_tier

    @display(description=_("Active"), boolean=True)
    def display_active(self, obj):
        return obj.is_active

    @display(description=_("Users"), ordering="_user_count")
    def user_count(self, obj):
        return obj._user_count

    @admin.action(description=_("Activate selected tenants"))
    def activate_tenants(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request, _("%(count)d tenant(s) activated.") % {"count": updated}, messages.SUCCESS
        )

    @admin.action(description=_("Deactivate selected tenants"))
    def deactivate_tenants(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request, _("%(count)d tenant(s) deactivated.") % {"count": updated}, messages.WARNING
        )


# ──────────────────────────────────────────────────────────────────────────────
# USER
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(User)
class UserAdmin(ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = [
        "display_header",
        "display_role",
        "tenant",
        "display_active",
        "display_verified",
        "display_locked",
        "last_login",
        "created_at",
    ]
    list_filter = [
        ("role", ChoicesDropdownFilter),
        ("tenant", RelatedDropdownFilter),
        "is_active",
        "is_email_verified",
        "is_staff",
        "is_superuser",
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["email", "full_name"]
    list_select_related = ["tenant"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True
    save_on_top = True
    list_per_page = 25
    inlines = [UserProfileInline, UserRoleAssignmentInline, UserRefreshTokenInline]

    readonly_fields = [
        "id",
        "created_at",
        "last_login",
        "last_login_ip",
        "failed_login_attempts",
        "locked_until",
        "password_last_changed",
        "deleted_at",
        "google_sub",
    ]

    fieldsets = (
        (
            _("Identity"),
            {
                "fields": ("id", "email", "full_name", "password", "role", "tenant"),
                "classes": ["tab"],
                "description": _(
                    "Core user identity. Role determines access level (superadmin, admin, client). "
                    "Tenant scopes data visibility — users only see records belonging to their tenant."
                ),
            },
        ),
        (
            _("Google OAuth"),
            {"fields": ("google_sub", "google_picture_url"), "classes": ["tab"],
             "description": _(
                 "Populated automatically when a user signs in via Google OAuth. "
                 "Google sub is the unique subject identifier from Google's ID token. Read-only."
             )},
        ),
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "is_email_verified"),
                "classes": ["tab"],
                "description": _(
                    "Standard Django permission flags. is_active controls login access — deactivate to block. "
                    "is_staff grants access to the admin panel. is_superuser bypasses all permission checks."
                ),
            },
        ),
        (
            _("Security"),
            {
                "fields": (
                    "last_login",
                    "last_login_ip",
                    "failed_login_attempts",
                    "locked_until",
                    "password_last_changed",
                ),
                "classes": ["tab"],
                "description": _(
                    "Login tracking and brute-force protection. After 5 consecutive failed attempts "
                    "the account is locked for 15 minutes. Use the 'Unlock' action to manually reset."
                ),
            },
        ),
        (
            _("Legal"),
            {"fields": ("terms_accepted_at", "privacy_accepted_version"), "classes": ["tab"],
             "description": _(
                 "GDPR and privacy compliance timestamps. Terms accepted date is set on first login. "
                 "Privacy accepted version tracks which version of the policy the user agreed to."
             )},
        ),
        (
            _("Audit"),
            {
                "fields": ("created_at", "created_by", "deleted_at", "deleted_by"),
                "classes": ["tab"],
                "description": _(
                    "Creation and soft-deletion tracking. Deleted users are hidden but retained for data integrity. "
                    "Created by records which staff member created this user account."
                ),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "tenant", "password1", "password2"),
            },
        ),
    )

    actions = [
        "activate_users",
        "deactivate_users",
        "verify_emails",
        "unlock_accounts",
        "revoke_sessions",
    ]
    actions_row = ["row_unlock_account"]

    # ── Display columns ────────────────────────────────────────────────────

    @display(description=_("User"), header=True)
    def display_header(self, obj):
        return [obj.full_name, obj.email, _initials(obj.full_name, obj.email[:1].upper())]

    @display(
        description=_("Role"),
        ordering="role",
        label={
            User.Role.SUPERADMIN: "danger",
            User.Role.ADMIN: "warning",
            User.Role.CLIENT: "info",
        },
    )
    def display_role(self, obj):
        return obj.role

    @display(description=_("Active"), boolean=True)
    def display_active(self, obj):
        return obj.is_active

    @display(description=_("Verified"), boolean=True)
    def display_verified(self, obj):
        return obj.is_email_verified

    @display(
        description=_("Locked"),
        label={True: "danger", False: "success"},
    )
    def display_locked(self, obj):
        return obj.is_locked

    # ── Bulk actions ───────────────────────────────────────────────────────

    @admin.action(description=_("Activate selected users"))
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request, _("%(count)d user(s) activated.") % {"count": updated}, messages.SUCCESS
        )

    @admin.action(description=_("Deactivate selected users"))
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request, _("%(count)d user(s) deactivated.") % {"count": updated}, messages.WARNING
        )

    @admin.action(description=_("Mark email as verified"))
    def verify_emails(self, request, queryset):
        updated = queryset.update(is_email_verified=True)
        self.message_user(
            request, _("%(count)d user(s) marked verified.") % {"count": updated}, messages.SUCCESS
        )

    @admin.action(description=_("Unlock accounts"))
    def unlock_accounts(self, request, queryset):
        updated = queryset.update(locked_until=None, failed_login_attempts=0)
        self.message_user(
            request, _("%(count)d account(s) unlocked.") % {"count": updated}, messages.SUCCESS
        )

    @admin.action(description=_("Revoke all active sessions"))
    def revoke_sessions(self, request, queryset):
        count = UserRefreshToken.objects.filter(user__in=queryset, revoked=False).update(
            revoked=True
        )
        self.message_user(
            request,
            _("%(count)d active session(s) revoked.") % {"count": count},
            messages.SUCCESS,
        )

    # ── Per-row quick action ──────────────────────────────────────────────

    @action(description=_("Unlock"), url_path="unlock-account")
    def row_unlock_account(self, request, object_id):
        user = self.get_object(request, object_id)
        if user is not None:
            user.reset_failed_login()
            messages.success(request, _("Account for %(email)s unlocked.") % {"email": user.email})
        return redirect(reverse("admin:accounts_user_change", args=[object_id]))


# ──────────────────────────────────────────────────────────────────────────────
# RBAC
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    list_display = ["codename", "name", "resource_type"]
    search_fields = ["codename", "name", "resource_type"]
    list_filter = ["resource_type"]
    readonly_fields = ["id"]
    list_filter_submit = True
    warn_unsaved_form = True


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ["name", "permission_count", "created_at"]
    search_fields = ["name"]
    filter_horizontal = ["permissions"]
    readonly_fields = ["id", "created_at"]
    warn_unsaved_form = True

    fieldsets = (
        (_("Role"), {"fields": ("id", "name", "permissions"), "classes": ["tab"],
         "description": _(
             "A named role groups one or more permissions. Assign roles to users via UserRoleAssignment. "
             "Permissions define what actions a user with this role can perform."
         )}),
        (_("Audit"), {"fields": ("created_at",), "classes": ["tab"],
         "description": _("Auto-managed timestamp.")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_permission_count=Count("permissions"))

    @display(description=_("Permissions"), ordering="_permission_count")
    def permission_count(self, obj):
        return obj._permission_count


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(ModelAdmin):
    list_display = ["user", "role", "display_active", "assigned_at", "expires_at"]
    list_filter = [("role", RelatedDropdownFilter)]
    search_fields = ["user__email", "role__name"]
    readonly_fields = ["id", "assigned_at"]
    autocomplete_fields = ["user", "role", "assigned_by"]
    list_filter_submit = True
    warn_unsaved_form = True

    fieldsets = (
        (_("Assignment"), {"fields": ("id", "user", "role", "assigned_by"), "classes": ["tab"],
         "description": _(
             "Assign a role to a user. The role's permissions are inherited by the user. "
             "Assigned by records which staff member created this assignment."
         )}),
        (_("Lifecycle"), {"fields": ("assigned_at", "expires_at"), "classes": ["tab"],
         "description": _(
             "Assignments can be time-limited via the expires_at field. "
             "Expired assignments are automatically considered inactive by the permission system."
         )}),
    )

    @display(description=_("Active"), label={True: "success", False: "danger"})
    def display_active(self, obj):
        return obj.is_active


# ──────────────────────────────────────────────────────────────────────────────
# SESSIONS
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(UserRefreshToken)
class UserRefreshTokenAdmin(ModelAdmin):
    list_display = [
        "user",
        "device_name",
        "ip_address",
        "display_revoked",
        "last_used_at",
        "expires_at",
    ]
    list_filter = ["revoked"]
    search_fields = ["user__email", "device_name", "ip_address"]
    readonly_fields = [
        "id",
        "jti",
        "user",
        "device_name",
        "ip_address",
        "user_agent",
        "last_used_at",
        "created_at",
    ]
    actions = ["revoke_selected"]
    list_filter_submit = True

    def has_add_permission(self, request):
        return False

    @display(description=_("Status"), label={True: "danger", False: "success"})
    def display_revoked(self, obj):
        return obj.revoked

    @admin.action(description=_("Revoke selected sessions"))
    def revoke_selected(self, request, queryset):
        updated = queryset.filter(revoked=False).update(revoked=True)
        self.message_user(
            request, _("%(count)d session(s) revoked.") % {"count": updated}, messages.SUCCESS
        )


# ──────────────────────────────────────────────────────────────────────────────
# TOKENS
# ──────────────────────────────────────────────────────────────────────────────


class _BaseTokenAdmin(ModelAdmin):
    list_display = ["user", "display_valid", "used", "expires_at", "created_at"]
    readonly_fields = ["id", "token_hash", "user", "used", "used_at", "created_at"]
    list_filter = ["used"]
    search_fields = ["user__email"]

    def has_add_permission(self, request):
        return False

    @display(description=_("Valid"), boolean=True)
    def display_valid(self, obj):
        return obj.is_valid


@admin.register(MagicLinkToken)
class MagicLinkTokenAdmin(_BaseTokenAdmin):
    list_filter_submit = True


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(_BaseTokenAdmin):
    list_filter_submit = True


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(_BaseTokenAdmin):
    list_filter_submit = True


# ──────────────────────────────────────────────────────────────────────────────
# MFA
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(UserMFA)
class UserMFAAdmin(ModelAdmin):
    list_display = ["user", "display_method", "display_active", "created_at"]
    list_filter = ["method", "is_active"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "user", "secret_encrypted", "created_at", "updated_at"]

    fieldsets = (
        (_("MFA"), {"fields": ("id", "user", "method", "is_active"), "classes": ["tab"],
         "description": _(
             "Multi-factor authentication configuration for this user. "
             "TOTP uses an authenticator app (e.g. Google Authenticator). "
             "WebAuthn uses biometric or hardware security keys."
         )}),
        (_("Audit"), {"fields": ("secret_encrypted", "created_at", "updated_at"), "classes": ["tab"],
         "description": _("Secret is encrypted at rest. Never expose the raw TOTP secret.")}),
    )

    @display(
        description=_("Method"),
        label={UserMFA.Method.TOTP: "info", UserMFA.Method.WEBAUTHN: "success"},
    )
    def display_method(self, obj):
        return obj.method

    @display(description=_("Active"), boolean=True)
    def display_active(self, obj):
        return obj.is_active