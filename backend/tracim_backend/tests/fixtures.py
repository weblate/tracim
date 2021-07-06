import logging
import os
import pathlib
import subprocess
import typing
import urllib.parse

from depot.manager import DepotManager
import plaster
from pyramid import testing
import pytest
import requests
from sqlalchemy import text
from sqlalchemy.event import listen
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy.pool import Pool
import transaction
from webtest import TestApp

from tracim_backend import CFG
from tracim_backend import init_models
from tracim_backend import web
from tracim_backend.app_models.applications import TracimApplicationInContext
from tracim_backend.app_models.contents import ContentTypeList
from tracim_backend.fixtures import FixturesLoader
from tracim_backend.fixtures.content import Content as ContentFixture
from tracim_backend.fixtures.users import Base as BaseFixture
from tracim_backend.fixtures.users import Test as FixtureTest
from tracim_backend.lib.rq import RqQueueName
from tracim_backend.lib.rq import get_redis_connection
from tracim_backend.lib.rq import get_rq_queue
from tracim_backend.lib.utils.logger import logger
from tracim_backend.lib.webdav import TracimDavProvider
from tracim_backend.lib.webdav import WebdavAppFactory
from tracim_backend.models.auth import Profile
from tracim_backend.models.auth import User
from tracim_backend.models.meta import DeclarativeBase
from tracim_backend.models.setup_models import get_session_factory
from tracim_backend.tests.utils import TEST_CONFIG_FILE_PATH
from tracim_backend.tests.utils import ApplicationApiFactory
from tracim_backend.tests.utils import ContentApiFactory
from tracim_backend.tests.utils import ElasticSearchHelper
from tracim_backend.tests.utils import EventHelper
from tracim_backend.tests.utils import MailHogHelper
from tracim_backend.tests.utils import MessageHelper
from tracim_backend.tests.utils import RadicaleServerHelper
from tracim_backend.tests.utils import RoleApiFactory
from tracim_backend.tests.utils import ShareLibFactory
from tracim_backend.tests.utils import SubscriptionLibFactory
from tracim_backend.tests.utils import TracimTestContext
from tracim_backend.tests.utils import UploadPermissionLibFactory
from tracim_backend.tests.utils import UserApiFactory
from tracim_backend.tests.utils import WedavEnvironFactory
from tracim_backend.tests.utils import WorkspaceApiFactory
from tracim_backend.tests.utils import find_free_port
from tracim_backend.tests.utils import tracim_plugin_loader

DATABASE_USER = "user"
DATABASE_PASSWORD = "secret"
DEFAULT_DATABASE_NAME = "tracim_test"


def wait_for_url(url):
    while True:
        try:
            requests.get(url)
            break
        except requests.exceptions.ConnectionError:
            pass


def create_database(url) -> None:
    """
    Create the database for server-based DB
    """
    u = urllib.parse.urlparse(url)
    if u.scheme == "postgresql":
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = psycopg2.connect(
            "host=localhost port={port} dbname={dbname} user={username} password={password}".format(
                dbname=DEFAULT_DATABASE_NAME,
                port=u.port,
                username=DATABASE_USER,
                password=DATABASE_PASSWORD,
            )
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE {}".format(u.path[1:]))
    elif u.scheme in ("mysql", "mariadb"):
        import pymysql

        conn = pymysql.connect(
            host="localhost",
            port=u.port,
            user="root",
            password=DATABASE_PASSWORD,
            db=DEFAULT_DATABASE_NAME,
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE {}".format(u.path[1:]))
        cursor.execute(
            "GRANT ALL ON {db_name}.* TO {user}".format(db_name=u.path[1:], user=DATABASE_USER)
        )


@pytest.fixture
def unique_name(worker_id: str) -> str:
    return "tracim_test__{}".format(worker_id)


@pytest.fixture()
def sqlalchemy_url(sqlalchemy_database, tmp_path, unique_name) -> str:
    DATABASE_URLS = {
        "sqlite": "sqlite:////{path}/{name}.sqlite".format(path=str(tmp_path), name=unique_name),
        "mysql": "mysql+pymysql://{username}:{password}@localhost:3306/{name}".format(
            name=unique_name, username=DATABASE_USER, password=DATABASE_PASSWORD
        ),
        "mariadb": "mysql+pymysql://{username}:{password}@localhost:3307/{name}".format(
            name=unique_name, username=DATABASE_USER, password=DATABASE_PASSWORD
        ),
        "postgresql": "postgresql://{username}:{password}@localhost:5432/{name}?client_encoding=utf8".format(
            name=unique_name, username=DATABASE_USER, password=DATABASE_PASSWORD
        ),
    }
    return DATABASE_URLS[sqlalchemy_database]

@pytest.fixture
def pushpin(tracim_webserver, tmp_path_factory, unique_name) -> str:
    pushpin_base = "http://localhost:7999/{}".format(unique_name)
    wait_for_url(pushpin_base)
    yield pushpin_base


@pytest.fixture
def rq_database_worker(config_uri, app_config):
    def empty_event_queues():
        redis_connection = get_redis_connection(app_config)
        for queue_name in RqQueueName:
            queue = get_rq_queue(redis_connection, queue_name)
            queue.delete()

    empty_event_queues()
    worker_env = os.environ.copy()
    worker_env["TRACIM_CONF_PATH"] = "{}#rq_worker_test".format(config_uri)
    base_args = ["rq", "worker", "-q", "-w", "tracim_backend.lib.rq.worker.DatabaseWorker"]
    queue_name_args = [queue_name.value for queue_name in RqQueueName]
    worker_process = subprocess.Popen(base_args + queue_name_args, env=worker_env,)

    yield worker_process
    empty_event_queues()
    worker_process.terminate()
    try:
        worker_process.wait(5.0)
    except TimeoutError:
        worker_process.kill()
        raise TimeoutError("rq worker didn't shut down properly, had to kill it")


@pytest.fixture
def tracim_webserver(
    settings, config_uri, engine, session_factory, config_section
) -> typing.Generator[subprocess.Popen, None, None]:
    config_filepath = pathlib.Path(__file__).parent.parent.parent / config_uri

    # NOTE SG 2020-12-22: those ports MUST be the same as the ones defined in
    # backend/pushpin_config/routes file
    start = 6543
    WORKER_ID_PORTS = {
        "master": start,
    }
    WORKER_ID_PORTS.update({"gw{}".format(index): start + index + 1 for index in range(8)})
    try:
        port = WORKER_ID_PORTS[worker_id]
    except KeyError:
        raise KeyError(
            "No defined port for worker {}. Add it in backend/pushpin_config/routes AND in WORKER_ID_PORTS"
        )
    listen = "localhost:{}".format(port)
    process = subprocess.Popen(
        [
            "pserve",
            str(config_filepath),
            "-n",
            "tracim_webserver",
            "--server-name",
            "tracim_webserver",
            "http_listen={}".format(listen)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    wait_for_url("http://{}".format(listen))
    yield server_process
    server_process.terminate()
    try:
        server_process.wait(5.0)
    except TimeoutError:
        server_process.kill()
        raise TimeoutError("tracim webserver didn't shut down properly, had to kill it")
    session_factory.close_all()


@pytest.fixture
def config_uri() -> str:
    return TEST_CONFIG_FILE_PATH


@pytest.fixture
def config_section(request) -> str:
    """This fixture is used by other fixtures to know which test config section to use.

    To change which config section name must be used for a test, use following decorator
    on your test:

        @pytest.mark.parametrize("config_section", [{"name": "<name_of_config_section>"}], indirect=True)
    """
    return getattr(request, "param", {}).get("name", "base_test")


@pytest.fixture
def settings(config_uri, config_section, sqlalchemy_url, tmp_path, unique_name):
    _settings = plaster.get_settings(config_uri, config_section)
    _settings["here"] = str(tmp_path)
    for path_setting in (
        "uploaded_files.storage.local.storage_path",
        "caldav.radicale.storage.filesystem_folder",
        "preview_cache_dir",
        "session.data_dir",
        "session.lock_dir",
    ):
        (tmp_path / path_setting).mkdir()
        _settings[path_setting] = str(tmp_path / path_setting)
    _settings["uploaded_files.storage.s3.bucket"] = unique_name

    port = find_free_port()
    _settings["caldav.radicale_proxy.base_url"] = "http://localhost:{}".format(port)

    os.environ["TRACIM_SQLALCHEMY__URL"] = sqlalchemy_url
    _settings["sqlalchemy.url"] = sqlalchemy_url

    _settings["search.elasticsearch.index_alias"] = unique_name

    os.environ["TRACIM_LIVE_MESSAGES__ASYNC_QUEUE_NAME"] = unique_name
    _settings["live_messages.async_queue_name"] = unique_name

    return _settings


@pytest.fixture
def config(settings):
    """This fixture initialize and return pyramid configurator"""
    yield testing.setUp(settings=settings)
    testing.tearDown()


@pytest.fixture
def app_config(settings) -> CFG:
    DepotManager._clear()
    config = CFG(settings)
    config.configure_filedepot()
    yield config
    DepotManager._clear()


@pytest.fixture
def web_testapp(settings, hapic, session):
    DepotManager._clear()
    app = web({}, **settings)
    return TestApp(app)


@pytest.fixture
def hapic():
    from tracim_backend.extensions import hapic as hapic_static

    # INFO - G.M - 2019-03-19 - Reset all hapic context: PyramidContext
    # and controllers
    hapic_static.reset_context()
    # TODO - G.M - 2019-03-19 - Replace this code by something better, see
    # https://github.com/algoo/hapic/issues/144
    hapic_static._controllers = []
    yield hapic_static
    hapic_static.reset_context()
    # TODO - G.M - 2019-03-19 - Replace this code by something better, see
    # https://github.com/algoo/hapic/issues/144
    hapic_static._controllers = []


@pytest.fixture
def engine(config, app_config):
    init_models(config, app_config)
    from tracim_backend.models.setup_models import get_engine

    is_sqlite = app_config.SQLALCHEMY__URL.startswith("sqlite")
    if is_sqlite:
        isolation_level = "SERIALIZABLE"

        def no_journal(dbapi_con, connection_record):
            dbapi_con.execute("PRAGMA JOURNAL_MODE=OFF")

        listen(Pool, "connect", no_journal)
    else:
        isolation_level = "READ_COMMITTED"
    try:
        engine = get_engine(app_config, isolation_level=isolation_level, pool_pre_ping=True)
        DeclarativeBase.metadata.create_all(engine, checkfirst=True)
    except OperationalError:
        engine.dispose()
        create_database(app_config.SQLALCHEMY__URL)
        engine = get_engine(app_config, isolation_level=isolation_level, pool_pre_ping=True)
        DeclarativeBase.metadata.create_all(engine)
    yield engine
    connection = engine.connect()
    with connection.begin():
        try:
            for table in reversed(DeclarativeBase.metadata.sorted_tables):
                connection.execute(table.delete())
        except (OperationalError, ProgrammingError):
            pass
    engine.dispose()


@pytest.fixture
def session_factory(engine):
    return get_session_factory(engine)


@pytest.fixture
def migration_engine(engine):
    yield engine
    sql = text("DROP TABLE IF EXISTS migrate_version;")
    engine.execute(sql)


@pytest.fixture()
def official_plugin_folder():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__))) + "/official_plugins"


@pytest.fixture()
def load_parent_access_plugin(test_context, official_plugin_folder):
    pluggy_manager = test_context.plugin_manager
    plugin_name = "tracim_backend_parent_access"
    return tracim_plugin_loader(plugin_name, pluggy_manager, official_plugin_folder)


@pytest.fixture()
def load_auto_invite_plugin(test_context, official_plugin_folder):
    pluggy_manager = test_context.plugin_manager
    plugin_name = "tracim_backend_autoinvite"
    return tracim_plugin_loader(plugin_name, pluggy_manager, official_plugin_folder)


@pytest.fixture()
def load_child_removal_plugin(test_context, official_plugin_folder):
    pluggy_manager = test_context.plugin_manager
    plugin_name = "tracim_backend_child_removal"
    return tracim_plugin_loader(plugin_name, pluggy_manager, official_plugin_folder)


@pytest.fixture
def test_context(app_config, session_factory):
    yield TracimTestContext(app_config, session_factory=session_factory)


@pytest.fixture
def test_context_without_plugins(app_config, session_factory):
    yield TracimTestContext(app_config, session_factory=session_factory, init_plugins=False)


@pytest.fixture
def session(request, engine, session_factory, app_config, test_logger, test_context):
    context = test_context
    yield context.dbsession
    context.dbsession.rollback()
    context.dbsession.close_all()
    transaction.abort()


@pytest.fixture
def base_fixture(session, app_config) -> Session:
    with transaction.manager:
        try:
            fixtures_loader = FixturesLoader(session, app_config)
            fixtures_loader.loads([BaseFixture])
        except IntegrityError as e:
            transaction.abort()
            raise e
    transaction.commit()
    return session


@pytest.fixture
def test_fixture(session, app_config) -> Session:
    """
    Warning! This fixture is now deprecated. Don't use it for new tests.
    """
    with transaction.manager:
        try:
            fixtures_loader = FixturesLoader(session, app_config)
            fixtures_loader.loads([FixtureTest])
        except IntegrityError as e:
            transaction.abort()
            raise e
    transaction.commit()
    return session


@pytest.fixture
def default_content_fixture(base_fixture, app_config) -> Session:
    """
    Warning! This fixture is now deprecated. Don't use it for new tests.
    """
    with transaction.manager:
        try:
            fixtures_loader = FixturesLoader(base_fixture, app_config)
            fixtures_loader.loads([ContentFixture])
        except IntegrityError as e:
            transaction.abort()
            raise e
    transaction.commit()
    return session


@pytest.fixture
def user_api_factory(session, app_config, admin_user) -> UserApiFactory:
    return UserApiFactory(session, app_config, admin_user)


@pytest.fixture
def workspace_api_factory(session, app_config, admin_user) -> WorkspaceApiFactory:
    return WorkspaceApiFactory(session, app_config, admin_user)


@pytest.fixture
def content_api_factory(session, app_config, admin_user) -> ContentApiFactory:
    return ContentApiFactory(session, app_config, admin_user)


@pytest.fixture
def share_lib_factory(session, app_config, admin_user) -> ShareLibFactory:
    return ShareLibFactory(session, app_config, admin_user)


@pytest.fixture
def upload_permission_lib_factory(session, app_config, admin_user) -> UploadPermissionLibFactory:
    return UploadPermissionLibFactory(session, app_config, admin_user)


@pytest.fixture
def role_api_factory(session, app_config, admin_user) -> RoleApiFactory:
    return RoleApiFactory(session, app_config, admin_user)


@pytest.fixture
def application_api_factory(app_list) -> ApplicationApiFactory:
    return ApplicationApiFactory(app_list)


@pytest.fixture
def subscription_lib_factory(session, app_config, admin_user) -> ApplicationApiFactory:
    return SubscriptionLibFactory(session, app_config, admin_user)


@pytest.fixture()
def admin_user(session: Session) -> User:
    return session.query(User).filter(User.email == "admin@admin.admin").one()


@pytest.fixture()
def bob_user(session: Session, user_api_factory: UserApiFactory) -> User:
    user = user_api_factory.get().create_user(
        email="bob@test.test",
        username="bob",
        password="password",
        name="bob",
        profile=Profile.USER,
        timezone="Europe/Paris",
        lang="fr",
        do_save=True,
        do_notify=False,
    )
    transaction.commit()
    return user


@pytest.fixture()
def riyad_user(session: Session, user_api_factory: UserApiFactory) -> User:
    user = user_api_factory.get().create_user(
        email="riyad@test.test",
        username="riyad",
        password="password",
        name="Riyad Faisal",
        profile=Profile.USER,
        timezone="Europe/Paris",
        lang="fr",
        do_save=True,
        do_notify=False,
    )
    transaction.commit()
    return user


@pytest.fixture()
def app_list() -> typing.List[TracimApplicationInContext]:
    from tracim_backend.extensions import app_list as application_list_static

    return application_list_static


@pytest.fixture()
def content_type_list() -> ContentTypeList:
    from tracim_backend.app_models.contents import content_type_list as content_type_list_static

    return content_type_list_static


@pytest.fixture()
def webdav_provider(app_config: CFG):
    return TracimDavProvider(app_config=app_config)


@pytest.fixture()
def webdav_environ_factory(
    webdav_provider: TracimDavProvider, session: Session, admin_user: User, app_config: CFG,
) -> WedavEnvironFactory:
    return WedavEnvironFactory(
        provider=webdav_provider, session=session, app_config=app_config, admin_user=admin_user,
    )


@pytest.fixture
def test_logger() -> None:
    """
    Set all logger to a high level to avoid getting too much noise for tests
    """
    logger._logger.setLevel("ERROR")
    logging.getLogger().setLevel("ERROR")
    logging.getLogger("sqlalchemy").setLevel("ERROR")
    logging.getLogger("txn").setLevel("ERROR")
    logging.getLogger("cliff").setLevel("ERROR")
    logging.getLogger("_jb_pytest_runner").setLevel("ERROR")
    return logger


@pytest.fixture
def mailhog() -> MailHogHelper:
    mailhog_helper = MailHogHelper()
    mailhog_helper.cleanup_mailhog()
    yield mailhog_helper
    mailhog_helper.cleanup_mailhog()


@pytest.fixture
def elasticsearch(app_config, session) -> ElasticSearchHelper:
    elasticsearch_helper = ElasticSearchHelper(app_config, session)
    yield elasticsearch_helper
    elasticsearch_helper.delete_indices()


@pytest.fixture
def radicale_server(settings) -> RadicaleServerHelper:
    radicale_server_helper = RadicaleServerHelper(settings)
    yield radicale_server_helper
    radicale_server_helper.stop_radicale_server()


@pytest.fixture
def webdav_testapp(config_uri, config_section) -> TestApp:
    DepotManager._clear()
    settings = plaster.get_settings(config_uri, config_section)
    settings["here"] = os.path.dirname(os.path.abspath(TEST_CONFIG_FILE_PATH))
    app_factory = WebdavAppFactory(**settings)
    app = app_factory.get_wsgi_app()
    return TestApp(app)


@pytest.fixture
def event_helper(session) -> EventHelper:
    return EventHelper(session)


@pytest.fixture
def message_helper(session) -> MessageHelper:
    return MessageHelper(session)


@pytest.fixture
def html_with_nasty_mention() -> str:
    return "<p> You are not a <img onerror='nastyXSSCall()' alt='member' /> of this workspace <span id='mention-victim'>@victimnotmemberofthisworkspace</span>, are you? </p>"
