"""Точка входа Alembic для выполнения миграций."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import config as _config
from app.database.models import *

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set sqlalchemy.url
config.set_main_option(
    "sqlalchemy.url", _config.config.db.build_connection_str() + "?async_fallback=true"
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base. metadata # noqa: F405

# other values from the config, defined by the needs of env.py,
# can be acquired: