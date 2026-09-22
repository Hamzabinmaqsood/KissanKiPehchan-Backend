from rest_framework.permissions import (
    BasePermission,
)


class IsDashboardEditor(BasePermission):
    """
    Editing is intentionally based on explicit role/permission,
    not is_staff.

    CustomUser.is_staff currently defaults to True in this project,
    so using DRF IsAdminUser would incorrectly allow ordinary users.
    """

    message = (
        "You do not have permission to edit "
        "the project dashboard."
    )

    EDIT_ROLE_NAMES = {
        "admin",
        "administrator",
        "ceo",
        "project manager",
        "project & commercial manager",
    }

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        if user.is_superuser:
            return True

        if user.has_perm(
            "project_dashboard.change_projectdashboard"
        ):
            return True

        role = getattr(
            user,
            "role",
            None,
        )

        role_name = (
            getattr(
                role,
                "name",
                "",
            )
            or ""
        ).strip().lower()

        return (
            role_name
            in self.EDIT_ROLE_NAMES
        )
