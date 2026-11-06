"""The admin pages of joining up initiatives: which of the pages every type has joining up initiatives use, and the ones only joining up initiatives have."""
from indigo import TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
from indigo.forms import JoiningUpInitiativeEditForm, JoiningUpInitiativeNewForm
from indigo.models import JoiningUpInitiative
from indigo.views_admin.generic.change_status import AdminModelChangeStatus
from indigo.views_admin.generic.edit import AdminModelEdit
from indigo.views_admin.generic.history import AdminModelHistory
from indigo.views_admin.generic.lists import AdminModelList
from indigo.views_admin.generic.moderate import AdminModelModerate
from indigo.views_admin.generic.new import AdminModelJSONFormNew
from indigo.views_admin.generic.records import AdminModelIndex


class AdminJoiningUpInitiativeList(AdminModelList):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Joining Up Initiatives"
    _noun_plural = "Joining Up Initiatives"
    _add_label = "Joining Up Initiative"
    _url_prefix = "joining_up_initiative"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeIndex(AdminModelIndex):
    _model = JoiningUpInitiative
    _record_title = "Joining Up Initiative"
    _list_title = "Joining Up Initiatives"
    _url_prefix = "joining_up_initiative"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeNew(AdminModelJSONFormNew):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _form_class = JoiningUpInitiativeNewForm
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeEdit(AdminModelEdit):
    _model = JoiningUpInitiative
    _record_title = "Joining Up Initiative"
    _list_title = "Joining Up Initiatives"
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _form_class = JoiningUpInitiativeEditForm
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeChangeStatus(AdminModelChangeStatus):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeModerate(AdminModelModerate):
    _model = JoiningUpInitiative
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeHistory(AdminModelHistory):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
