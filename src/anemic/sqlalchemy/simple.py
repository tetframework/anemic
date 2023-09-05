from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlalchemy


from typing import Type, Any, Optional

import anemic.services
from pyramid.config import Configurator

# Recommended naming convention used by Alembic, as various different database
# providers will autogenerate vastly different names making migrations more
# difficult. See: http://alembic.zzzcomputing.com/en/latest/naming.html
from pyramid.request import Request
from zope.interface import Interface

DEFAULT_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def declarative_base(*, metadata=None, naming_convention=None) -> Any:
    """
    Create a declarative base, using the given naming convention, defaulting
    to the DEFAULT_NAMING_CONVENTION of this module

    :return: the newly created declarative_base
    """
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.schema import MetaData

    if naming_convention is None:
        naming_convention = DEFAULT_NAMING_CONVENTION

    if metadata is None:
        metadata = MetaData(naming_convention=naming_convention)

    return declarative_base(metadata=metadata)


def get_tm_session(session_factory, transaction_manager):
    """
    Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.
    This function will hook the session to the transaction manager which
    will take care of committing any changes.
    - When using pyramid_tm it will automatically be committed or aborted
      depending on whether an exception is raised.
    - When using scripts you should wrap the session in a manager yourself.
      For example::
          import transaction
          engine = get_engine(settings)
          session_factory = get_session_factory(engine)
          with transaction.manager:
              dbsession = get_tm_session(session_factory, transaction.manager)
    """
    import zope.sqlalchemy

    dbsession = session_factory()
    zope.sqlalchemy.register(dbsession, transaction_manager=transaction_manager)
    return dbsession


def setup_sqlalchemy(
    config: Configurator,
    *,
    settings: Optional[dict] = None,
    prefix: str = "sqlalchemy.",
    engine: Optional["sqlalchemy.Engine"] = None,
    name: str = "",
) -> None:
    """
    Sets up SQLAlchemy, creating a request scoped service for the ORM session.
    Include all models before calling this configurator.

    :param config: the configurator
    :param base: The declarative base class. Required
    :param settings: Optional settings dictionary for the engine creation
    :param prefix: Optional settings prefix for the engine settings
    :param engine: The engine to use - if specified, settings must not be
                given, or vice versa
    :param name: the alternate name for which to bind the session service
    """

    from sqlalchemy import engine_from_config
    from sqlalchemy.orm import sessionmaker, Session, configure_mappers, scoped_session

    if settings is not None:
        if engine is not None:
            raise ValueError("Only one of settings, " "engine may be specified")
    else:
        settings = config.registry.settings

    if engine is None:
        engine = engine_from_config(settings, prefix)

    session_factory = sessionmaker()
    session_factory.configure(bind=engine)

    if "anemic.sqlalchemy.simple.factories" not in config.registry:
        config.registry["anemic.sqlalchemy.simple.factories"] = {}

    config.registry["anemic.sqlalchemy.simple.factories"][name] = session_factory

    def _session_service(context: Any, request: Request):
        return get_tm_session(session_factory, request.tm)

    config.register_service_factory(_session_service, Session, Interface, name=name)

    config.register_service(
        scoped_session(session_factory),
        name="scoped_session" + (":" + name if name else ""),
    )

    config.action("anemic.sqlalchemy.simple.configure_mappers", configure_mappers)


def includeme(config: Configurator) -> None:
    """
    Include the simple SQLAlchemy configuration with reasonable defaults.

    :param config: the configurator
    """
    try:
        import sqlalchemy
    except ImportError as e:
        raise RuntimeError(
            "sqlalchemy cannot be imported, "
            "unable to include anemic.sqlalchemy.simple"
        ) from e

    config.include("pyramid_services")

    settings = config.get_settings()
    settings["tm.manager_hook"] = "pyramid_tm.explicit_manager"

    # use pyramid_tm to hook the transaction lifecycle to the request
    config.include("pyramid_tm")

    config.add_directive("setup_sqlalchemy", setup_sqlalchemy)
