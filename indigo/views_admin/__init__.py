"""The admin pages of the app (under /app/admin/), split by area. Everything is re-exported here so urls.py can say views_admin.<name>."""
from .change_status import (  # noqa: F401
    AdminAssessmentResourceChangeStatus,
    AdminFundChangeStatus,
    AdminJoiningUpInitiativeChangeStatus,
    AdminModelChangeStatus,
    AdminOrganisationChangeStatus,
    AdminPipelineChangeStatus,
    AdminProjectChangeStatus,
)
from .common import (  # noqa: F401
    permission_admin_or_data_steward_required,
    user_can_access_edit,
    user_can_access_event,
    user_can_access_project,
)
from .dashboard import admin_index  # noqa: F401
from .data_quality import (  # noqa: F401
    AdminModelDataQualityReport,
    AdminPipelineDataQualityReport,
    AdminProjectDataQualityReport,
    admin_all_projects_data_quality_list_projects_by_priority_highest,
    admin_all_projects_data_quality_report,
    admin_all_projects_data_quality_report_field_list,
    admin_all_projects_data_quality_report_field_single,
)
from .downloads import (  # noqa: F401
    AdminAssessmentResourceDownloadBlankForm,
    AdminAssessmentResourceDownloadForm,
    AdminFundDownloadBlankForm,
    AdminFundDownloadForm,
    AdminModelDownloadBlankForm,
    AdminModelDownloadForm,
    AdminPipelineDownloadBlankForm,
    AdminPipelineDownloadForm,
    AdminProjectDownloadBlankForm,
    AdminProjectDownloadBlankSimpleForm,
    AdminProjectDownloadForm,
    AdminProjectDownloadSimpleForm,
)
from .edit import (  # noqa: F401
    AdminAssessmentResourceEdit,
    AdminFundEdit,
    AdminJoiningUpInitiativeEdit,
    AdminModelEdit,
    AdminOrganisationEdit,
    AdminPipelineEdit,
    AdminProjectEdit,
)
from .history import (  # noqa: F401
    AdminAssessmentResourceHistory,
    AdminFundHistory,
    AdminJoiningUpInitiativeHistory,
    AdminModelHistory,
    AdminPipelineHistory,
    admin_edit_index,
    admin_event_index,
    admin_history,
)
from .imports import (  # noqa: F401
    AdminAssessmentResourceImportForm,
    AdminFundImportForm,
    AdminModelImportForm,
    AdminModelImportFormStage1Of2,
    AdminModelImportFormStage2Of2,
    AdminPipelineImportFormStage1Of2,
    AdminPipelineImportFormStage2Of2,
    AdminProjectImportFormStage1Of2,
    AdminProjectImportFormStage2Of2,
)
from .lists import (  # noqa: F401
    AdminAssessmentResourceList,
    AdminFundList,
    AdminJoiningUpInitiativeList,
    AdminModelList,
    AdminPipelineList,
)
from .moderate import (  # noqa: F401
    AdminAssessmentResourceModerate,
    AdminFundModerate,
    AdminJoiningUpInitiativeModerate,
    AdminModelModerate,
    AdminPipelineModerate,
)
from .new import (  # noqa: F401
    AdminAssessmentResourceNew,
    AdminFundNew,
    AdminJoiningUpInitiativeNew,
    AdminModelJSONFormNew,
    AdminModelNew,
    AdminPipelineNew,
)
from .organisations import (  # noqa: F401
    admin_organisation_download_all_csv,
    admin_organisation_download_blank_form,
    admin_organisation_download_form,
    admin_organisation_history,
    admin_organisation_import_form,
    admin_organisation_index,
    admin_organisation_moderate,
    admin_organisation_pipelines,
    admin_organisation_projects,
    admin_organisations_goto,
    admin_organisations_new,
    admin_organisations_search,
    admin_organisations_search_json,
)
from .projects import (  # noqa: F401
    admin_project_admin_users,
    admin_project_history,
    admin_project_index,
    admin_project_moderate,
    admin_projects_list,
    admin_projects_new,
)
from .records import (  # noqa: F401
    AdminAssessmentResourceIndex,
    AdminFundIndex,
    AdminJoiningUpInitiativeIndex,
    AdminModelIndex,
    AdminPipelineIndex,
    admin_fund_projects,
)
from .sandboxes import admin_sandbox_index, admin_sandbox_list  # noqa: F401
from .to_moderate import admin_to_moderate  # noqa: F401
