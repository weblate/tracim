from http import HTTPStatus
import json
import typing

from hapic import HapicData
from hapic.data import HapicFile
from pyramid.config import Configurator
from pyramid.response import Response

from tracim_backend.config import CFG
from tracim_backend.error import ErrorCode
from tracim_backend.exceptions import CannotGetDepotFileDepotCorrupted
from tracim_backend.exceptions import CannotUseBothIncludeAndExcludeWorkspaceUsers
from tracim_backend.exceptions import EmailAlreadyExists
from tracim_backend.exceptions import ExternalAuthUserEmailModificationDisallowed
from tracim_backend.exceptions import ExternalAuthUserPasswordModificationDisallowed
from tracim_backend.exceptions import InvalidWorkspaceAccessType
from tracim_backend.exceptions import MessageDoesNotExist
from tracim_backend.exceptions import MimetypeNotAllowed
from tracim_backend.exceptions import NoFileValidationError
from tracim_backend.exceptions import NotFound
from tracim_backend.exceptions import PageOfPreviewNotFound
from tracim_backend.exceptions import PasswordDoNotMatch
from tracim_backend.exceptions import PreviewDimNotAllowed
from tracim_backend.exceptions import ReservedUsernameError
from tracim_backend.exceptions import RoleAlreadyExistError
from tracim_backend.exceptions import TooManyOnlineUsersError
from tracim_backend.exceptions import TooShortAutocompleteString
from tracim_backend.exceptions import TracimFileNotFound
from tracim_backend.exceptions import TracimValidationFailed
from tracim_backend.exceptions import UnavailablePreview
from tracim_backend.exceptions import UserCantChangeIsOwnProfile
from tracim_backend.exceptions import UserCantDeleteHimself
from tracim_backend.exceptions import UserCantDisableHimself
from tracim_backend.exceptions import UserFollowAlreadyDefined
from tracim_backend.exceptions import UserImageNotFound
from tracim_backend.exceptions import UsernameAlreadyExists
from tracim_backend.exceptions import UserSelfRegistrationDisabledException
from tracim_backend.exceptions import WorkspaceNotFound
from tracim_backend.exceptions import WrongUserPassword
from tracim_backend.extensions import hapic
from tracim_backend.lib.core.content import ContentApi
from tracim_backend.lib.core.event import EventApi
from tracim_backend.lib.core.live_messages import LiveMessagesLib
from tracim_backend.lib.core.live_messages import ServerSideEventType
from tracim_backend.lib.core.subscription import SubscriptionLib
from tracim_backend.lib.core.user import DEFAULT_AVATAR_SIZE
from tracim_backend.lib.core.user import DEFAULT_COVER_SIZE
from tracim_backend.lib.core.user import UserApi
from tracim_backend.lib.core.user_custom_properties import UserCustomPropertiesApi
from tracim_backend.lib.core.userconfig import UserConfigApi
from tracim_backend.lib.core.workspace import WorkspaceApi
from tracim_backend.lib.utils.authorization import check_right
from tracim_backend.lib.utils.authorization import has_personal_access
from tracim_backend.lib.utils.authorization import is_administrator
from tracim_backend.lib.utils.authorization import knows_candidate_user
from tracim_backend.lib.utils.logger import logger
from tracim_backend.lib.utils.request import TracimRequest
from tracim_backend.lib.utils.utils import generate_documentation_swagger_tag
from tracim_backend.lib.utils.utils import password_generator
from tracim_backend.models.auth import AuthType
from tracim_backend.models.auth import Profile
from tracim_backend.models.auth import UserCreationType
from tracim_backend.models.context_models import AboutUser
from tracim_backend.models.context_models import PaginatedObject
from tracim_backend.models.context_models import UserMessagesSummary
from tracim_backend.models.context_models import WorkspaceInContext
from tracim_backend.models.data import WorkspaceSubscription
from tracim_backend.models.event import Message
from tracim_backend.models.event import ReadStatus
from tracim_backend.views.controllers import Controller
from tracim_backend.views.core_api.schemas import AboutUserSchema
from tracim_backend.views.core_api.schemas import ContentDigestSchema
from tracim_backend.views.core_api.schemas import ContentIdsQuerySchema
from tracim_backend.views.core_api.schemas import DeleteFollowedUserPathSchema
from tracim_backend.views.core_api.schemas import FileQuerySchema
from tracim_backend.views.core_api.schemas import FollowedUsersSchemaPage
from tracim_backend.views.core_api.schemas import GetLiveMessageQuerySchema
from tracim_backend.views.core_api.schemas import GetUserFollowQuerySchema
from tracim_backend.views.core_api.schemas import KnownContentsQuerySchema
from tracim_backend.views.core_api.schemas import KnownMembersQuerySchema
from tracim_backend.views.core_api.schemas import LiveMessageSchemaPage
from tracim_backend.views.core_api.schemas import MessageIdsPathSchema
from tracim_backend.views.core_api.schemas import NoContentSchema
from tracim_backend.views.core_api.schemas import ReadStatusSchema
from tracim_backend.views.core_api.schemas import SetConfigSchema
from tracim_backend.views.core_api.schemas import SetCustomPropertiesSchema
from tracim_backend.views.core_api.schemas import SetEmailSchema
from tracim_backend.views.core_api.schemas import SetPasswordSchema
from tracim_backend.views.core_api.schemas import SetUserAllowedSpaceSchema
from tracim_backend.views.core_api.schemas import SetUserInfoSchema
from tracim_backend.views.core_api.schemas import SetUsernameSchema
from tracim_backend.views.core_api.schemas import SetUserProfileSchema
from tracim_backend.views.core_api.schemas import SimpleFileSchema
from tracim_backend.views.core_api.schemas import TracimLiveEventHeaderSchema
from tracim_backend.views.core_api.schemas import TracimLiveEventQuerySchema
from tracim_backend.views.core_api.schemas import UserConfigSchema
from tracim_backend.views.core_api.schemas import UserCreationSchema
from tracim_backend.views.core_api.schemas import UserDigestSchema
from tracim_backend.views.core_api.schemas import UserDiskSpaceSchema
from tracim_backend.views.core_api.schemas import UserIdPathSchema
from tracim_backend.views.core_api.schemas import UserIdSchema
from tracim_backend.views.core_api.schemas import UserMessagesMarkAsReadQuerySchema
from tracim_backend.views.core_api.schemas import UserMessagesSummaryQuerySchema
from tracim_backend.views.core_api.schemas import UserMessagesSummarySchema
from tracim_backend.views.core_api.schemas import UserPicturePathSchema
from tracim_backend.views.core_api.schemas import UserPreviewPicturePathSchema
from tracim_backend.views.core_api.schemas import UserSchema
from tracim_backend.views.core_api.schemas import UserWorkspaceAndContentIdPathSchema
from tracim_backend.views.core_api.schemas import UserWorkspaceFilterQuerySchema
from tracim_backend.views.core_api.schemas import UserWorkspaceIdPathSchema
from tracim_backend.views.core_api.schemas import WorkspaceIdSchema
from tracim_backend.views.core_api.schemas import WorkspaceSchema
from tracim_backend.views.core_api.schemas import WorkspaceSubscriptionSchema
from tracim_backend.views.swagger_generic_section import SWAGGER_TAG__CONTENT_ENDPOINTS
from tracim_backend.views.swagger_generic_section import SWAGGER_TAG__ENABLE_AND_DISABLE_SECTION
from tracim_backend.views.swagger_generic_section import SWAGGER_TAG__NOTIFICATION_SECTION
from tracim_backend.views.swagger_generic_section import SWAGGER_TAG__TRASH_AND_RESTORE_SECTION
from tracim_backend.views.swagger_generic_section import SWAGGER_TAG_EVENT_ENDPOINTS
from tracim_backend.views.swagger_generic_section import SWAGGER_TAG_USER_CONFIG_ENDPOINTS
from tracim_backend.views.swagger_generic_section import SWAGGER_TAG_USER_SUBSCRIPTIONS_SECTION

SWAGGER_TAG__USER_ENDPOINTS = "Users"

SWAGGER_TAG__USER_TRASH_AND_RESTORE_ENDPOINTS = generate_documentation_swagger_tag(
    SWAGGER_TAG__USER_ENDPOINTS, SWAGGER_TAG__TRASH_AND_RESTORE_SECTION
)

SWAGGER_TAG__USER_ENABLE_AND_DISABLE_ENDPOINTS = generate_documentation_swagger_tag(
    SWAGGER_TAG__USER_ENDPOINTS, SWAGGER_TAG__ENABLE_AND_DISABLE_SECTION
)

SWAGGER_TAG__USER_CONTENT_ENDPOINTS = generate_documentation_swagger_tag(
    SWAGGER_TAG__USER_ENDPOINTS, SWAGGER_TAG__CONTENT_ENDPOINTS
)

SWAGGER_TAG__USER_NOTIFICATION_ENDPOINTS = generate_documentation_swagger_tag(
    SWAGGER_TAG__USER_ENDPOINTS, SWAGGER_TAG__NOTIFICATION_SECTION
)

SWAGGER_TAG__USER_EVENT_ENDPOINTS = generate_documentation_swagger_tag(
    SWAGGER_TAG__USER_ENDPOINTS, SWAGGER_TAG_EVENT_ENDPOINTS
)

SWAGGER_TAG__USER_CONFIG_ENDPOINTS = generate_documentation_swagger_tag(
    SWAGGER_TAG__USER_ENDPOINTS, SWAGGER_TAG_USER_CONFIG_ENDPOINTS
)

SWAGGER_TAG__USER_SUBSCRIPTIONS_ENDPOINTS = generate_documentation_swagger_tag(
    SWAGGER_TAG__USER_ENDPOINTS, SWAGGER_TAG_USER_SUBSCRIPTIONS_SECTION
)

ALLOWED__AVATAR_MIMETYPES = [
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/bmp",
    "image/x-ms-bmp",
    "image/gif",
]


class UserController(Controller):
    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONTENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_query(UserWorkspaceFilterQuerySchema())
    @hapic.output_body(WorkspaceSchema(many=True))
    def user_workspace(self, context, request: TracimRequest, hapic_data=None):
        """
        Get list of user workspaces
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        wapi = WorkspaceApi(
            current_user=request.candidate_user,  # User
            session=request.dbsession,
            config=app_config,
        )

        workspaces = wapi.get_all_for_user(
            request.candidate_user,
            include_owned=hapic_data.query.show_owned_workspace,
            include_with_role=hapic_data.query.show_workspace_with_role,
            parents_ids=hapic_data.query.parent_ids,
        )
        return [wapi.get_workspace_with_context(workspace) for workspace in workspaces]

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONTENT_ENDPOINTS])
    @hapic.handle_exception(WorkspaceNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(RoleAlreadyExistError, HTTPStatus.BAD_REQUEST)
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_body(WorkspaceIdSchema())
    @hapic.output_body(WorkspaceSchema())
    def join_workspace(self, context, request: TracimRequest, hapic_data=None):
        """
        Join a workspace.
        Only possible for OPEN workspaces.
        Subscribing to a ON_REQUEST workspace is done through /api/users/<user_id>/workspace_subscriptions.
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        wapi = WorkspaceApi(
            current_user=request.candidate_user,  # User
            session=request.dbsession,
            config=app_config,
        )
        workspace = wapi.add_current_user_as_member(workspace_id=hapic_data.body["workspace_id"])
        return wapi.get_workspace_with_context(workspace)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(UserSchema())
    def user(self, context, request: TracimRequest, hapic_data=None):
        """
        Get user infos.
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        return uapi.get_user_with_context(request.candidate_user)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(UserDiskSpaceSchema())
    def user_disk_space(self, context, request: TracimRequest, hapic_data=None):
        """
        Get user space infos.
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        return uapi.get_user_with_context(request.candidate_user)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(is_administrator)
    @hapic.output_body(UserSchema(many=True))
    def users(self, context, request: TracimRequest, hapic_data=None):
        """
        Get all users
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        users = uapi.get_all()
        context_users = [uapi.get_user_with_context(user) for user in users]
        return context_users

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_query(KnownMembersQuerySchema())
    @hapic.output_body(UserDigestSchema(many=True))
    @hapic.handle_exception(CannotUseBothIncludeAndExcludeWorkspaceUsers, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(TooShortAutocompleteString, HTTPStatus.BAD_REQUEST)
    def known_members(self, context, request: TracimRequest, hapic_data=None):
        """
        Get known users list
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.candidate_user,  # User
            session=request.dbsession,
            config=app_config,
            show_deactivated=False,
        )
        users = uapi.get_known_users(
            acp=hapic_data.query.acp,
            exclude_user_ids=hapic_data.query.exclude_user_ids,
            exclude_workspace_ids=hapic_data.query.exclude_workspace_ids,
            include_workspace_ids=hapic_data.query.include_workspace_ids,
            limit=hapic_data.query.limit,
            filter_results=app_config.KNOWN_MEMBERS__FILTER,
        )
        context_users = [uapi.get_user_with_context(user) for user in users]
        return context_users

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_query(KnownContentsQuerySchema())
    @hapic.output_body(ContentDigestSchema(many=True))
    @hapic.handle_exception(CannotUseBothIncludeAndExcludeWorkspaceUsers, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(TooShortAutocompleteString, HTTPStatus.BAD_REQUEST)
    def known_contents(self, context, request: TracimRequest, hapic_data=None):
        """
        Get known contents list
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.candidate_user,
            session=request.dbsession,
            config=app_config,
            show_deactivated=False,
        )
        context_contents = uapi.get_known_contents_in_context(
            acp=hapic_data.query.acp, limit=hapic_data.query.limit
        )
        return context_contents

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @hapic.handle_exception(WrongUserPassword, HTTPStatus.FORBIDDEN)
    @hapic.handle_exception(EmailAlreadyExists, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(ExternalAuthUserEmailModificationDisallowed, HTTPStatus.BAD_REQUEST)
    @check_right(has_personal_access)
    @hapic.input_body(SetEmailSchema())
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(UserSchema())
    def set_user_email(self, context, request: TracimRequest, hapic_data=None):
        """
        Set user Email
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        user = uapi.set_email(
            request.candidate_user,
            hapic_data.body.loggedin_user_password,
            hapic_data.body.email,
            do_save=True,
        )
        return uapi.get_user_with_context(user)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @hapic.handle_exception(WrongUserPassword, HTTPStatus.FORBIDDEN)
    @hapic.handle_exception(UsernameAlreadyExists, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(ReservedUsernameError, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(TracimValidationFailed, HTTPStatus.BAD_REQUEST)
    @check_right(has_personal_access)
    @hapic.input_body(SetUsernameSchema())
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(UserSchema())
    def set_user_username(self, context, request: TracimRequest, hapic_data=None):
        """
        Set user username
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        user = uapi.set_username(
            request.candidate_user,
            hapic_data.body.loggedin_user_password,
            hapic_data.body.username,
            do_save=True,
        )
        return uapi.get_user_with_context(user)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @hapic.handle_exception(WrongUserPassword, HTTPStatus.FORBIDDEN)
    @hapic.handle_exception(PasswordDoNotMatch, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(ExternalAuthUserPasswordModificationDisallowed, HTTPStatus.BAD_REQUEST)
    @check_right(has_personal_access)
    @hapic.input_body(SetPasswordSchema())
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_user_password(self, context, request: TracimRequest, hapic_data=None):
        """
        Set user password
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        uapi.set_password(
            request.candidate_user,
            hapic_data.body.loggedin_user_password,
            hapic_data.body.new_password,
            hapic_data.body.new_password2,
            do_save=True,
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_body(SetUserInfoSchema())
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(UserSchema())
    def set_user_infos(self, context, request: TracimRequest, hapic_data=None):
        """
        Set user info data
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        user = uapi.update(
            request.candidate_user,
            auth_type=request.candidate_user.auth_type,
            name=hapic_data.body.public_name,
            timezone=hapic_data.body.timezone,
            lang=hapic_data.body.lang,
            do_save=True,
        )
        return uapi.get_user_with_context(user)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @hapic.handle_exception(EmailAlreadyExists, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(UsernameAlreadyExists, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(ReservedUsernameError, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(TracimValidationFailed, HTTPStatus.BAD_REQUEST)
    @check_right(is_administrator)
    @hapic.input_body(UserCreationSchema())
    @hapic.output_body(UserSchema())
    def create_user(self, context, request: TracimRequest, hapic_data=None):
        """
        Create new user. Note: One of username or email required.
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        if hapic_data.body.profile:
            profile = Profile.get_profile_from_slug(hapic_data.body.profile)
        else:
            profile = None
        password = hapic_data.body.password
        if not password and hapic_data.body.email_notification:
            password = password_generator()

        user = uapi.create_user(
            auth_type=AuthType.UNKNOWN,
            email=hapic_data.body.email,
            password=password,
            timezone=hapic_data.body.timezone,
            lang=hapic_data.body.lang,
            name=hapic_data.body.public_name,
            username=hapic_data.body.username,
            do_notify=hapic_data.body.email_notification,
            allowed_space=hapic_data.body.allowed_space,
            creation_type=UserCreationType.ADMIN,
            creation_author=request.current_user,
            profile=profile,
            do_save=True,
        )
        return uapi.get_user_with_context(user)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @hapic.handle_exception(EmailAlreadyExists, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(UsernameAlreadyExists, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(ReservedUsernameError, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(TracimValidationFailed, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(UserSelfRegistrationDisabledException, HTTPStatus.BAD_REQUEST)
    @hapic.input_body(UserCreationSchema())
    @hapic.output_body(UserSchema())
    def register_user(self, context, request: TracimRequest, hapic_data=None):
        """
        Register a new user (this is a public endpoint)
        """
        if not request.app_config.USER__SELF_REGISTRATION__ENABLED:
            raise UserSelfRegistrationDisabledException("Self registration is disabled")
        uapi = UserApi(
            current_user=None, session=request.dbsession, config=request.app_config  # User
        )
        do_notify = (
            request.app_config.EMAIL__NOTIFICATION__ACTIVATED
            and request.app_config.NEW_USER__INVITATION__DO_NOTIFY
            and request.app_config.JOBS__PROCESSING_MODE == request.app_config.CST.SYNC
        )
        user = uapi.create_user(
            auth_type=AuthType.UNKNOWN,
            email=hapic_data.body.email,
            password=hapic_data.body.password,
            timezone=hapic_data.body.timezone,
            lang=hapic_data.body.lang,
            name=hapic_data.body.public_name,
            username=hapic_data.body.username,
            creation_type=UserCreationType.REGISTER,
            do_save=True,
            do_notify=do_notify,
        )
        return uapi.get_user_with_context(user)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENABLE_AND_DISABLE_ENDPOINTS])
    @check_right(is_administrator)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def enable_user(self, context, request: TracimRequest, hapic_data=None):
        """
        enable user
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        uapi.enable(user=request.candidate_user, do_save=True)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_TRASH_AND_RESTORE_ENDPOINTS])
    @hapic.handle_exception(UserCantDeleteHimself, HTTPStatus.BAD_REQUEST)
    @check_right(is_administrator)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def delete_user(self, context, request: TracimRequest, hapic_data=None):
        """
        delete user
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        uapi.delete(user=request.candidate_user, do_save=True)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_TRASH_AND_RESTORE_ENDPOINTS])
    @check_right(is_administrator)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def undelete_user(self, context, request: TracimRequest, hapic_data=None):
        """
        undelete user
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user,  # User
            session=request.dbsession,
            config=app_config,
            show_deleted=True,
        )
        uapi.undelete(user=request.candidate_user, do_save=True)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENABLE_AND_DISABLE_ENDPOINTS])
    @hapic.handle_exception(UserCantDisableHimself, HTTPStatus.BAD_REQUEST)
    @check_right(is_administrator)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def disable_user(self, context, request: TracimRequest, hapic_data=None):
        """
        disable user
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        uapi.disable(user=request.candidate_user, do_save=True)
        return

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @hapic.handle_exception(UserCantChangeIsOwnProfile, HTTPStatus.BAD_REQUEST)
    @check_right(is_administrator)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_body(SetUserProfileSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_profile(self, context, request: TracimRequest, hapic_data=None):
        """
        set user profile
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        profile = Profile.get_profile_from_slug(hapic_data.body.profile)
        uapi.update(
            user=request.candidate_user,
            auth_type=request.candidate_user.auth_type,
            profile=profile,
            do_save=True,
        )
        return

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(is_administrator)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_body(SetUserAllowedSpaceSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_allowed_space(self, context, request: TracimRequest, hapic_data=None):
        """
        set user allowed_space
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        uapi = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        uapi.update(
            user=request.candidate_user,
            auth_type=request.candidate_user.auth_type,
            allowed_space=hapic_data.body.allowed_space,
            do_save=True,
        )
        return

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONTENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserWorkspaceIdPathSchema())
    @hapic.input_query(ContentIdsQuerySchema())
    @hapic.output_body(ReadStatusSchema(many=True))
    def contents_read_status(self, context, request: TracimRequest, hapic_data=None):
        """
        get user_read status of contents
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        content_api = ContentApi(
            current_user=request.candidate_user,  # User
            session=request.dbsession,
            config=app_config,
        )
        wapi = WorkspaceApi(
            current_user=request.candidate_user,  # User
            session=request.dbsession,
            config=app_config,
        )
        workspace = None
        if hapic_data.path.workspace_id:
            workspace = wapi.get_one(hapic_data.path.workspace_id)
        last_actives = content_api.get_last_active(
            workspace=workspace,
            limit=None,
            before_content=None,
            content_ids=hapic_data.query.content_ids or None,
        )
        return [content_api.get_content_in_context(content) for content in last_actives]

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONTENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserWorkspaceAndContentIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_content_as_read(self, context, request: TracimRequest, hapic_data=None):
        """
        set user_read status of content to read
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        content_api = ContentApi(
            show_archived=True,
            show_deleted=True,
            current_user=request.candidate_user,
            session=request.dbsession,
            config=app_config,
        )
        content_api.mark_read(request.current_content, do_flush=True)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONTENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserWorkspaceAndContentIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_content_as_unread(self, context, request: TracimRequest, hapic_data=None):
        """
        set user_read status of content to unread
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        content_api = ContentApi(
            show_archived=True,
            show_deleted=True,
            current_user=request.candidate_user,
            session=request.dbsession,
            config=app_config,
        )
        content_api.mark_unread(request.current_content, do_flush=True)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONTENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserWorkspaceIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_workspace_as_read(self, context, request: TracimRequest, hapic_data=None):
        """
        set user_read status of all content of workspace to read
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        content_api = ContentApi(
            show_archived=True,
            show_deleted=True,
            current_user=request.candidate_user,
            session=request.dbsession,
            config=app_config,
        )
        content_api.mark_read__workspace(request.current_workspace)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_NOTIFICATION_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserWorkspaceIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def enable_workspace_notification(self, context, request: TracimRequest, hapic_data=None):
        """
        enable workspace notification
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        wapi = WorkspaceApi(
            current_user=request.candidate_user,  # User
            session=request.dbsession,
            config=app_config,
        )
        workspace = wapi.get_one(hapic_data.path.workspace_id)
        wapi.enable_notifications(request.candidate_user, workspace)
        wapi.save(workspace)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_NOTIFICATION_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserWorkspaceIdPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def disable_workspace_notification(self, context, request: TracimRequest, hapic_data=None):
        """
        disable workspace notification
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        wapi = WorkspaceApi(
            current_user=request.candidate_user,  # User
            session=request.dbsession,
            config=app_config,
        )
        workspace = wapi.get_one(hapic_data.path.workspace_id)
        wapi.disable_notifications(request.candidate_user, workspace)
        wapi.save(workspace)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_EVENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_query(GetLiveMessageQuerySchema())
    @hapic.output_body(LiveMessageSchemaPage())
    def get_user_messages(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> PaginatedObject:
        """
        Returns user messages matching the given query
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        event_api = EventApi(request.current_user, request.dbsession, app_config)
        return PaginatedObject(
            event_api.get_paginated_messages_for_user(
                user_id=request.candidate_user.user_id,
                read_status=hapic_data.query.read_status,
                page_token=hapic_data.query.page_token,
                count=hapic_data.query.count,
                exclude_author_ids=hapic_data.query.exclude_author_ids,
                include_event_types=hapic_data.query.include_event_types,
                exclude_event_types=hapic_data.query.exclude_event_types,
                workspace_ids=hapic_data.query.workspace_ids,
                include_not_sent=hapic_data.query.include_not_sent,
                related_to_content_ids=hapic_data.query.related_to_content_ids,
            )
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_EVENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_query(UserMessagesSummaryQuerySchema())
    @hapic.output_body(UserMessagesSummarySchema())
    def get_user_messages_summary(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> UserMessagesSummary:
        """
        Returns a summary about messages filtered
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        event_api = EventApi(request.current_user, request.dbsession, app_config)
        candidate_user = UserApi(
            request.current_user, request.dbsession, app_config
        ).get_user_with_context(request.candidate_user)
        unread_messages_count = event_api.get_messages_count(
            user_id=candidate_user.user_id,
            read_status=ReadStatus.UNREAD,
            include_event_types=hapic_data.query.include_event_types,
            exclude_event_types=hapic_data.query.exclude_event_types,
            exclude_author_ids=hapic_data.query.exclude_author_ids,
            include_not_sent=hapic_data.query.include_not_sent,
            workspace_ids=hapic_data.query.workspace_ids,
            related_to_content_ids=hapic_data.query.related_to_content_ids,
        )
        read_messages_count = event_api.get_messages_count(
            user_id=candidate_user.user_id,
            read_status=ReadStatus.READ,
            include_event_types=hapic_data.query.include_event_types,
            exclude_event_types=hapic_data.query.exclude_event_types,
            exclude_author_ids=hapic_data.query.exclude_author_ids,
            include_not_sent=hapic_data.query.include_not_sent,
            workspace_ids=hapic_data.query.workspace_ids,
            related_to_content_ids=hapic_data.query.related_to_content_ids,
        )
        return UserMessagesSummary(
            user=candidate_user,
            unread_messages_count=unread_messages_count,
            read_messages_count=read_messages_count,
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_EVENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_query(UserMessagesMarkAsReadQuerySchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_user_messages_as_read(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> None:
        """
        Read all unread message for user
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        event_api = EventApi(request.current_user, request.dbsession, app_config)
        event_api.mark_user_messages_as_read(
            request.candidate_user.user_id,
            content_ids=hapic_data.query.content_ids,
            parent_ids=hapic_data.query.parent_ids,
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_EVENT_ENDPOINTS])
    @hapic.handle_exception(MessageDoesNotExist, http_code=HTTPStatus.BAD_REQUEST)
    @check_right(has_personal_access)
    @hapic.input_path(MessageIdsPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_message_as_read(self, context, request: TracimRequest, hapic_data: HapicData) -> None:
        """
        Read one message
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        event_api = EventApi(request.current_user, request.dbsession, app_config)
        event_api.mark_user_message_as_read(
            event_id=hapic_data.path.event_id, user_id=request.candidate_user.user_id
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_EVENT_ENDPOINTS])
    @hapic.handle_exception(MessageDoesNotExist, http_code=HTTPStatus.BAD_REQUEST)
    @check_right(has_personal_access)
    @hapic.input_path(MessageIdsPathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_message_as_unread(self, context, request: TracimRequest, hapic_data: HapicData) -> None:
        """
        unread one message
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        event_api = EventApi(request.current_user, request.dbsession, app_config)
        event_api.mark_user_message_as_unread(
            event_id=hapic_data.path.event_id, user_id=request.candidate_user.user_id
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_EVENT_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_headers(TracimLiveEventHeaderSchema())
    @hapic.input_query(TracimLiveEventQuerySchema())
    def open_message_stream(self, context, request: TracimRequest, hapic_data) -> Response:
        """
        Open the message stream for the given user.
        Tracim Live Message Events as ServerSide Event Stream
        """

        headers = [
            # content type for SSE
            ("Content-Type", "text/event-stream"),
            # do not cache the events
            ("Cache-Control", "no-cache"),
        ]

        app_config = request.registry.settings["CFG"]  # type: CFG
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )

        try:
            user_api.check_maximum_online_users()
        except TooManyOnlineUsersError as exc:
            message = str(exc)
            logger.warning(self, message)
            error = {
                "code": exc.error_code.value,
                "message": message,
            }
            response_body = LiveMessagesLib.get_server_side_event_string(
                ServerSideEventType.STREAM_ERROR, data=error, comment="Too many online users"
            )
            return Response(
                headerlist=headers, charset="utf-8", status_code=200, body=response_body
            )

        response_body = LiveMessagesLib.get_server_side_event_string(
            event_type=ServerSideEventType.STREAM_OPEN,
            data=None,
            comment="Tracim Live Messages for user {}".format(request.candidate_user.user_id),
        )
        after_event_id = hapic_data.query["after_event_id"]  # type: int
        if after_event_id:
            app_config = request.registry.settings["CFG"]  # type: CFG
            event_api = EventApi(request.current_user, request.dbsession, app_config)
            messages = event_api.get_messages_for_user(
                request.candidate_user.user_id, after_event_id=after_event_id
            )  # type: typing.List[Message]

            response_body += "".join(
                [
                    "data:" + json.dumps(LiveMessagesLib.message_as_dict(message)) + "\n\n"
                    for message in messages
                ]
            )

        escaped_keepalive_event = "event: keep-alive\\ndata:\\n\\n"
        user_channel_name = LiveMessagesLib.user_grip_channel(request.candidate_user.user_id)
        headers.extend(
            (
                # Here we ask push pin to keep the connection open
                ("Grip-Hold", "stream"),
                # and register this connection on the given channel
                # multiple channels subscription is possible
                ("Grip-Channel", user_channel_name),
                (
                    "Grip-Keep-Alive",
                    "{}; format=cstring; timeout=30".format(escaped_keepalive_event),
                ),
                # content type for SSE
                ("Content-Type", "text/event-stream"),
                # do not cache the events
                ("Cache-Control", "no-cache"),
            )
        )

        return Response(headerlist=headers, charset="utf-8", status_code=200, body=response_body)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONFIG_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(UserConfigSchema())
    def get_user_config(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> typing.Dict:
        """
        get all the configuration parameters for the given user
        """
        config_api = UserConfigApi(current_user=request.candidate_user, session=request.dbsession)
        return {"parameters": config_api.get_all_params()}

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONFIG_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_body(SetConfigSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_user_config(self, context, request: TracimRequest, hapic_data: HapicData) -> None:
        """
        Set or update the given configuration parameters for the given user
        The behavior of this endpoint is adding/updating key (patch-like) but not replacing the
        whole configuration, so it's not possible to remove keys through this endpoint.
        """
        config_api = UserConfigApi(current_user=request.candidate_user, session=request.dbsession)
        config_api.set_params(params=hapic_data.body["parameters"])

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONFIG_ENDPOINTS])
    @check_right(knows_candidate_user)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(UserConfigSchema())
    def get_user_custom_properties(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> typing.Dict:
        """
        get the custom properties parameters for the given user
        """
        custom_properties_api = UserCustomPropertiesApi(
            current_user=request.candidate_user,
            session=request.dbsession,
            app_config=request.app_config,
        )
        return {"parameters": custom_properties_api.get_all_params()}

    # TODO - G.M - 2021-01-13 - Permission should be adapted to be usable to all know_user
    # as complex right rules will be delegated to properties, see #4004
    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONFIG_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.handle_exception(TracimValidationFailed, HTTPStatus.BAD_REQUEST)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_body(SetCustomPropertiesSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def set_user_custom_properties(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> None:
        """
        Set or update the given custom_properties parameters for the given user
        The behavior of this endpoint is adding/updating key (patch-like) but not replacing the
        whole configuration, so it's not possible to remove keys through this endpoint.
        """
        custom_properties_api = UserCustomPropertiesApi(
            current_user=request.candidate_user,
            session=request.dbsession,
            app_config=request.app_config,
        )
        custom_properties_api.set_params(params=hapic_data.body["parameters"])

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_CONFIG_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(WorkspaceSchema(many=True))
    def get_accessible_workspaces(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> typing.List[WorkspaceInContext]:
        """
        Return the list of accessible workspaces by the given user id.
        An accessible workspace is:
          - a workspace the user is not member of (`workspaces` API returns them)
          - has an OPEN or ON_REQUEST access type
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        wapi = WorkspaceApi(
            current_user=request.candidate_user, session=request.dbsession, config=app_config
        )

        workspaces = wapi.get_all_accessible_by_user(request.candidate_user)
        return [wapi.get_workspace_with_context(workspace) for workspace in workspaces]

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_SUBSCRIPTIONS_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(WorkspaceSubscriptionSchema(many=True))
    def user_subscriptions(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> typing.List[WorkspaceSubscription]:
        subscription_lib = SubscriptionLib(
            current_user=request.current_user, session=request.dbsession, config=request.app_config
        )
        return subscription_lib.get_user_subscription(request.candidate_user.user_id)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_SUBSCRIPTIONS_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.handle_exception(InvalidWorkspaceAccessType, HTTPStatus.BAD_REQUEST)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_body(WorkspaceIdSchema())
    @hapic.output_body(WorkspaceSubscriptionSchema())
    def submit_subscription(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> typing.List[WorkspaceSubscription]:
        workspace = WorkspaceApi(
            current_user=None, session=request.dbsession, config=request.app_config
        ).get_one(hapic_data.body["workspace_id"])
        subscription_lib = SubscriptionLib(
            current_user=request.current_user, session=request.dbsession, config=request.app_config
        )
        return subscription_lib.submit_subscription(workspace=workspace)

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_query(GetUserFollowQuerySchema())
    @hapic.output_body(FollowedUsersSchemaPage())
    def following(self, context, request: TracimRequest, hapic_data: HapicData) -> PaginatedObject:
        """
        For given user, get list of following user ids.
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        return PaginatedObject(
            user_api.get_paginated_leaders_for_user(
                user_id=request.candidate_user.user_id,
                page_token=hapic_data.query.page_token,
                count=hapic_data.query.count,
                filter_leader_id=hapic_data.query.user_id,
            )
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_body(UserIdSchema())
    @hapic.handle_exception(UserFollowAlreadyDefined, http_code=HTTPStatus.BAD_REQUEST)
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.CREATED)
    def create_following(self, context, request: TracimRequest, hapic_data: HapicData) -> None:
        """
        Declare given user follow an other user.
        If following already exist, return a 400 error with {error_code} error code.
        """.format(
            error_code=ErrorCode.USER_FOLLOW_ALREADY_DEFINED
        )
        app_config = request.registry.settings["CFG"]  # type: CFG
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        user_api.create_follower(
            follower_id=hapic_data.path["user_id"], leader_id=hapic_data.body["user_id"]
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(DeleteFollowedUserPathSchema())
    @hapic.handle_exception(NotFound, http_code=HTTPStatus.BAD_REQUEST)
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def delete_following(self, context, request: TracimRequest, hapic_data: HapicData) -> None:
        """
        Delete given user following.
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        user_api.delete_follower(
            follower_id=hapic_data.path["user_id"], leader_id=hapic_data.path["leader_id"]
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.input_path(UserIdPathSchema())
    @hapic.input_query(GetUserFollowQuerySchema())
    @hapic.output_body(FollowedUsersSchemaPage())
    def followers(self, context, request: TracimRequest, hapic_data: HapicData) -> PaginatedObject:
        """
        For given user, get list of following user ids.
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        return PaginatedObject(
            user_api.get_paginated_followers_for_leader(
                user_id=request.candidate_user.user_id,
                page_token=hapic_data.query.page_token,
                count=hapic_data.query.count,
                filter_user_id=hapic_data.query.user_id,
            )
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(knows_candidate_user)
    @hapic.input_path(UserIdPathSchema())
    @hapic.output_body(AboutUserSchema())
    def about_user(self, context, request: TracimRequest, hapic_data: HapicData) -> AboutUser:
        """
        Return public user profile.
        """
        app_config = request.registry.settings["CFG"]  # type: CFG
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=app_config  # User
        )
        return user_api.get_about_user(hapic_data.path["user_id"])

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(knows_candidate_user)
    @hapic.input_query(FileQuerySchema())
    @hapic.input_path(UserPreviewPicturePathSchema())
    @hapic.handle_exception(UnavailablePreview, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(PageOfPreviewNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(PreviewDimNotAllowed, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(UserImageNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.output_file([])
    def sized_preview_avatar(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> HapicFile:
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=request.app_config
        )
        default_filename = "avatar_{width}x{height}.jpg".format(
            width=hapic_data.path.width, height=hapic_data.path.height,
        )
        return user_api.get_avatar_preview(
            request.candidate_user.user_id,
            filename=hapic_data.path.filename,
            default_filename=default_filename,
            width=hapic_data.path.width,
            height=hapic_data.path.height,
            force_download=hapic_data.query.force_download,
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(knows_candidate_user)
    @hapic.input_query(FileQuerySchema())
    @hapic.input_path(UserPicturePathSchema())
    @hapic.handle_exception(UnavailablePreview, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(PageOfPreviewNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(PreviewDimNotAllowed, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(UserImageNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.output_file([])
    def get_preview_avatar(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> HapicFile:
        width = DEFAULT_AVATAR_SIZE.width
        height = DEFAULT_AVATAR_SIZE.height
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=request.app_config
        )
        default_filename = "avatar.jpg".format(width=width, height=height)
        return user_api.get_avatar_preview(
            request.candidate_user.user_id,
            filename=hapic_data.path.filename,
            default_filename=default_filename,
            width=width,
            height=height,
            force_download=hapic_data.query.force_download,
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(knows_candidate_user)
    @hapic.input_query(FileQuerySchema())
    @hapic.input_path(UserPicturePathSchema())
    @hapic.handle_exception(UserImageNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.output_file([])
    def get_raw_avatar(self, context, request: TracimRequest, hapic_data: HapicData) -> HapicFile:
        try:
            user_api = UserApi(
                current_user=request.current_user,
                session=request.dbsession,
                config=request.app_config,
            )
            default_filename = "avatar.jpg"
            return user_api.get_avatar(
                request.candidate_user.user_id,
                filename=hapic_data.path.filename,
                default_filename=default_filename,
                force_download=hapic_data.query.force_download,
            )
        except CannotGetDepotFileDepotCorrupted as exc:
            raise TracimFileNotFound(
                "avatar for user {} not found in depot.".format(request.candidate_user.user_id)
            ) from exc

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.handle_exception(NoFileValidationError, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(MimetypeNotAllowed, HTTPStatus.BAD_REQUEST)
    @hapic.input_files(SimpleFileSchema())
    @hapic.input_path(UserPicturePathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def put_raw_avatar(self, context, request: TracimRequest, hapic_data: HapicData) -> None:
        if hapic_data.files.files is None:
            raise NoFileValidationError('No file "files" given at input, validation failed.')
        if hapic_data.files.files.type not in ALLOWED__AVATAR_MIMETYPES:
            raise MimetypeNotAllowed(
                "File mimetype {} is not allowed for avatar".format(hapic_data.files.files.type)
            )

        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=request.app_config
        )
        user_api.set_avatar(
            user_id=request.candidate_user.user_id,
            new_filename=hapic_data.files.files.filename,
            new_mimetype=hapic_data.files.files.type,
            new_content=hapic_data.files.files.file,
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(knows_candidate_user)
    @hapic.input_query(FileQuerySchema())
    @hapic.input_path(UserPreviewPicturePathSchema())
    @hapic.handle_exception(UnavailablePreview, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(PageOfPreviewNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(PreviewDimNotAllowed, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(UserImageNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.output_file([])
    def sized_preview_cover(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> HapicFile:
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=request.app_config
        )
        default_filename = "cover_{width}x{height}.jpg".format(
            width=hapic_data.path.width, height=hapic_data.path.height,
        )
        return user_api.get_cover_preview(
            request.candidate_user.user_id,
            filename=hapic_data.path.filename,
            default_filename=default_filename,
            width=hapic_data.path.width,
            height=hapic_data.path.height,
            force_download=hapic_data.query.force_download,
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(knows_candidate_user)
    @hapic.input_query(FileQuerySchema())
    @hapic.input_path(UserPicturePathSchema())
    @hapic.handle_exception(UnavailablePreview, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(PageOfPreviewNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(PreviewDimNotAllowed, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(UserImageNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.output_file([])
    def get_preview_cover(
        self, context, request: TracimRequest, hapic_data: HapicData
    ) -> HapicFile:
        width = DEFAULT_COVER_SIZE.width
        height = DEFAULT_COVER_SIZE.height
        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=request.app_config
        )
        default_filename = "cover.jpg".format(width=width, height=height)
        return user_api.get_cover_preview(
            request.candidate_user.user_id,
            filename=hapic_data.path.filename,
            default_filename=default_filename,
            width=width,
            height=height,
            force_download=hapic_data.query.force_download,
        )

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(knows_candidate_user)
    @hapic.input_query(FileQuerySchema())
    @hapic.input_path(UserPicturePathSchema())
    @hapic.handle_exception(UserImageNotFound, HTTPStatus.BAD_REQUEST)
    @hapic.output_file([])
    def get_raw_cover(self, context, request: TracimRequest, hapic_data: HapicData) -> HapicFile:
        try:
            user_api = UserApi(
                current_user=request.current_user,
                session=request.dbsession,
                config=request.app_config,
            )
            default_filename = "cover.jpg"
            return user_api.get_cover(
                request.candidate_user.user_id,
                filename=hapic_data.path.filename,
                default_filename=default_filename,
                force_download=hapic_data.query.force_download,
            )
        except CannotGetDepotFileDepotCorrupted as exc:
            raise TracimFileNotFound(
                "cover for user {} not found in depot.".format(request.candidate_user.user_id)
            ) from exc

    @hapic.with_api_doc(tags=[SWAGGER_TAG__USER_ENDPOINTS])
    @check_right(has_personal_access)
    @hapic.handle_exception(NoFileValidationError, HTTPStatus.BAD_REQUEST)
    @hapic.handle_exception(MimetypeNotAllowed, HTTPStatus.BAD_REQUEST)
    @hapic.input_files(SimpleFileSchema())
    @hapic.input_path(UserPicturePathSchema())
    @hapic.output_body(NoContentSchema(), default_http_code=HTTPStatus.NO_CONTENT)
    def put_raw_cover(self, context, request: TracimRequest, hapic_data: HapicData) -> None:
        if hapic_data.files.files is None:
            raise NoFileValidationError('No file "files" given at input, validation failed.')
        if hapic_data.files.files.type not in ALLOWED__AVATAR_MIMETYPES:
            raise MimetypeNotAllowed(
                "File mimetype {} is not allowed for cover".format(hapic_data.files.files.type)
            )

        user_api = UserApi(
            current_user=request.current_user, session=request.dbsession, config=request.app_config
        )
        user_api.set_cover(
            user_id=request.candidate_user.user_id,
            new_filename=hapic_data.files.files.filename,
            new_mimetype=hapic_data.files.files.type,
            new_content=hapic_data.files.files.file,
        )

    def bind(self, configurator: Configurator) -> None:
        """
        Create all routes and views using pyramid configurator
        for this controller
        """

        # user workspace
        configurator.add_route(
            "get_user_workspace",
            "/users/{user_id:\d+}/workspaces",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.user_workspace, route_name="get_user_workspace")
        configurator.add_route(
            "post_user_workspace",
            "/users/{user_id:\d+}/workspaces",
            request_method="POST",  # noqa: W605
        )
        configurator.add_view(self.join_workspace, route_name="post_user_workspace")

        # user info
        configurator.add_route("user", "/users/{user_id:\d+}", request_method="GET")  # noqa: W605
        configurator.add_view(self.user, route_name="user")

        # user space info
        configurator.add_route(
            "user_disk_space", "/users/{user_id:\d+}/disk_space", request_method="GET"
        )  # noqa: W605
        configurator.add_view(self.user_disk_space, route_name="user_disk_space")

        # users lists
        configurator.add_route("users", "/users", request_method="GET")
        configurator.add_view(self.users, route_name="users")

        # known members list
        configurator.add_route(
            "known_members",
            "/users/{user_id:\d+}/known_members",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.known_members, route_name="known_members")

        # known contents list
        configurator.add_route(
            "known_contents",
            "/users/{user_id:\d+}/known_contents",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.known_contents, route_name="known_contents")

        # set user email
        configurator.add_route(
            "set_user_email", "/users/{user_id:\d+}/email", request_method="PUT"
        )  # noqa: W605
        configurator.add_view(self.set_user_email, route_name="set_user_email")

        # set user username
        configurator.add_route(
            "set_user_username", "/users/{user_id:\d+}/username", request_method="PUT"
        )  # noqa: W605
        configurator.add_view(self.set_user_username, route_name="set_user_username")

        # set user password
        configurator.add_route(
            "set_user_password", "/users/{user_id:\d+}/password", request_method="PUT"  # noqa: W605
        )
        configurator.add_view(self.set_user_password, route_name="set_user_password")

        # set user_info
        configurator.add_route(
            "set_user_info", "/users/{user_id:\d+}", request_method="PUT"
        )  # noqa: W605
        configurator.add_view(self.set_user_infos, route_name="set_user_info")

        # create user
        configurator.add_route("create_user", "/users", request_method="POST")
        configurator.add_view(self.create_user, route_name="create_user")

        # register user (public endpoint)
        configurator.add_route("register_user", "/users/register", request_method="POST")
        configurator.add_view(self.register_user, route_name="register_user")

        # enable user
        configurator.add_route(
            "enable_user", "/users/{user_id:\d+}/enabled", request_method="PUT"
        )  # noqa: W605
        configurator.add_view(self.enable_user, route_name="enable_user")

        # disable user
        configurator.add_route(
            "disable_user", "/users/{user_id:\d+}/disabled", request_method="PUT"  # noqa: W605
        )
        configurator.add_view(self.disable_user, route_name="disable_user")

        # delete user
        configurator.add_route(
            "delete_user", "/users/{user_id:\d+}/trashed", request_method="PUT"
        )  # noqa: W605
        configurator.add_view(self.delete_user, route_name="delete_user")

        # undelete user
        configurator.add_route(
            "undelete_user",
            "/users/{user_id:\d+}/trashed/restore",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.undelete_user, route_name="undelete_user")

        # set user profile
        configurator.add_route(
            "set_user_profile", "/users/{user_id:\d+}/profile", request_method="PUT"  # noqa: W605
        )
        configurator.add_view(self.set_profile, route_name="set_user_profile")

        # set user allowed_space
        configurator.add_route(
            "set_user_allowed_space",
            "/users/{user_id:\d+}/allowed_space",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.set_allowed_space, route_name="set_user_allowed_space")

        # user content
        configurator.add_route(
            "contents_read_status",
            "/users/{user_id:\d+}/workspaces/{workspace_id}/contents/read_status",  # noqa: W605
            request_method="GET",
        )
        configurator.add_view(self.contents_read_status, route_name="contents_read_status")

        # set content as read/unread
        configurator.add_route(
            "read_content",
            "/users/{user_id:\d+}/workspaces/{workspace_id}/contents/{content_id}/read",  # noqa: W605
            request_method="PUT",
        )
        configurator.add_view(self.set_content_as_read, route_name="read_content")
        configurator.add_route(
            "unread_content",
            "/users/{user_id:\d+}/workspaces/{workspace_id}/contents/{content_id}/unread",  # noqa: W605
            request_method="PUT",
        )
        configurator.add_view(self.set_content_as_unread, route_name="unread_content")

        # set workspace as read
        configurator.add_route(
            "read_workspace",
            "/users/{user_id:\d+}/workspaces/{workspace_id}/read",  # noqa: W605
            request_method="PUT",
        )
        configurator.add_view(self.set_workspace_as_read, route_name="read_workspace")

        # enable workspace notification
        configurator.add_route(
            "enable_workspace_notification",
            "/users/{user_id:\d+}/workspaces/{workspace_id}/notifications/activate",  # noqa: W605
            request_method="PUT",
        )
        configurator.add_view(
            self.enable_workspace_notification, route_name="enable_workspace_notification"
        )

        # enable workspace notification
        configurator.add_route(
            "disable_workspace_notification",
            "/users/{user_id:\d+}/workspaces/{workspace_id}/notifications/deactivate",  # noqa: W605
            request_method="PUT",
        )
        configurator.add_view(
            self.disable_workspace_notification, route_name="disable_workspace_notification"
        )
        # TracimLiveMessages notification
        configurator.add_route(
            "live_messages",
            "/users/{user_id:\d+}/live_messages",  # noqa: W605
            request_method="GET",
        )
        configurator.add_view(self.open_message_stream, route_name="live_messages")

        # Tracim user messages
        configurator.add_route(
            "messages", "/users/{user_id:\d+}/messages", request_method="GET"  # noqa: W605
        )
        configurator.add_view(self.get_user_messages, route_name="messages")

        configurator.add_route(
            "messages_summary",
            "/users/{user_id:\d+}/messages/summary",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.get_user_messages_summary, route_name="messages_summary")

        # read all unread messages for user
        configurator.add_route(
            "read_messages",
            "/users/{user_id:\d+}/messages/read",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.set_user_messages_as_read, route_name="read_messages")

        # read all unread messages for user
        configurator.add_route(
            "read_message",
            "/users/{user_id:\d+}/messages/{event_id:\d+}/read",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.set_message_as_read, route_name="read_message")

        # read all unread messages for user
        configurator.add_route(
            "unread_message",
            "/users/{user_id:\d+}/messages/{event_id:\d+}/unread",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.set_message_as_unread, route_name="unread_message")

        # User configuration
        configurator.add_route(
            "config_get", "/users/{user_id:\d+}/config", request_method="GET"  # noqa: W605
        )
        configurator.add_view(self.get_user_config, route_name="config_get")

        configurator.add_route(
            "config_post", "/users/{user_id:\d+}/config", request_method="PUT"  # noqa: W605
        )
        configurator.add_view(self.set_user_config, route_name="config_post")

        # User custom properties
        configurator.add_route(
            "custom_properties_get",
            "/users/{user_id:\d+}/custom-properties",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.get_user_custom_properties, route_name="custom_properties_get")

        configurator.add_route(
            "custom_properties_post",
            "/users/{user_id:\d+}/custom-properties",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.set_user_custom_properties, route_name="custom_properties_post")

        # User accessible workspaces (not member of, but can see information about them to subscribe)
        configurator.add_route(
            "get_accessible_workspaces",
            "/users/{user_id:\d+}/accessible_workspaces",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(
            self.get_accessible_workspaces, route_name="get_accessible_workspaces"
        )

        # User subscriptions
        configurator.add_route(
            "subscriptions_get",
            "/users/{user_id:\d+}/workspace_subscriptions",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.user_subscriptions, route_name="subscriptions_get")

        configurator.add_route(
            "subscriptions_put",
            "/users/{user_id:\d+}/workspace_subscriptions",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.submit_subscription, route_name="subscriptions_put")

        # User following/followers
        configurator.add_route(
            "following", "/users/{user_id:\d+}/following", request_method="GET"  # noqa: W605
        )
        configurator.add_view(self.following, route_name="following")

        configurator.add_route(
            "create_following",
            "/users/{user_id:\d+}/following",
            request_method="POST",  # noqa: W605
        )
        configurator.add_view(self.create_following, route_name="create_following")

        configurator.add_route(
            "delete_following",
            "/users/{user_id:\d+}/following/{leader_id:\d+}",
            request_method="DELETE",  # noqa: W605
        )
        configurator.add_view(self.delete_following, route_name="delete_following")

        configurator.add_route(
            "followers", "/users/{user_id:\d+}/followers", request_method="GET"  # noqa: W605
        )
        configurator.add_view(self.followers, route_name="followers")

        configurator.add_route(
            "about_user", "/users/{user_id:\d+}/about", request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.about_user, route_name="about_user")

        configurator.add_route(
            "sized_preview_avatar",
            "/users/{user_id:\d+}/avatar/preview/jpg/{width:\d+}x{height:\d+}/{filename:[^/]*}",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.sized_preview_avatar, route_name="sized_preview_avatar")

        configurator.add_route(
            "get_preview_avatar",
            "/users/{user_id:\d+}/avatar/preview/jpg/{filename:[^/]*}",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.get_preview_avatar, route_name="get_preview_avatar")

        configurator.add_route(
            "get_raw_avatar",
            "/users/{user_id:\d+}/avatar/raw/{filename:[^/]*}",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.get_raw_avatar, route_name="get_raw_avatar")

        configurator.add_route(
            "put_raw_avatar",
            "/users/{user_id:\d+}/avatar/raw/{filename:[^/]*}",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.put_raw_avatar, route_name="put_raw_avatar")

        configurator.add_route(
            "sized_preview_cover",
            "/users/{user_id:\d+}/cover/preview/jpg/{width:\d+}x{height:\d+}/{filename:[^/]*}",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.sized_preview_cover, route_name="sized_preview_cover")

        configurator.add_route(
            "get_preview_cover",
            "/users/{user_id:\d+}/cover/preview/jpg/{filename:[^/]*}",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.get_preview_cover, route_name="get_preview_cover")

        configurator.add_route(
            "get_raw_cover",
            "/users/{user_id:\d+}/cover/raw/{filename:[^/]*}",
            request_method="GET",  # noqa: W605
        )
        configurator.add_view(self.get_raw_cover, route_name="get_raw_cover")

        configurator.add_route(
            "put_raw_cover",
            "/users/{user_id:\d+}/cover/raw/{filename:[^/]*}",
            request_method="PUT",  # noqa: W605
        )
        configurator.add_view(self.put_raw_cover, route_name="put_raw_cover")
