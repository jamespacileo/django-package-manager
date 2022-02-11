import tempfile
import os
from urlparse import urlparse

import json
import requests

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.schema import Table

if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.abspath('..'))

from django_package_manager.pip_bootstrap import PIPBootstrap

DJPM_LOCAL_DIR = os.path.abspath(os.path.dirname(__file__))
DJPM_TEMP_DIR = os.path.join(tempfile.gettempdir(), "django-package-manager")
if not os.path.exists(DJPM_TEMP_DIR):
    os.mkdir(DJPM_TEMP_DIR)
SQLITE_DB_FILENAME = os.path.join(DJPM_LOCAL_DIR, "djpm.db")
sqlite_connection_string = URL(drivername='sqlite', database=SQLITE_DB_FILENAME)
engine = create_engine(sqlite_connection_string, echo=False)

Base = declarative_base()
Session = sessionmaker(bind=engine)

association_table = Table('association', Base.metadata,
    Column('category_id', Integer, ForeignKey('categories.id')),
    Column('package_id', Integer, ForeignKey('packages.id'))
)

class VirtualEnvironment(Base):

    __tablename__ = 'virtual_environments'

    id = Column(Integer, primary_key=True)

    title = Column(String, index=True)
    directory_path = Column(String, unique=True)

    @property
    def scripts_dir(self):
        return ''

    @property
    def bin_dir(self):
        return ''

    def check_existance(self):
        return False

    @property
    def python_executable(self):
        return ''

class Category(Base):
    __tablename__ = 'categories'
    #objects = sessionmaker(bind=engine)

    id = Column(Integer, primary_key=True)

    absolute_url = Column(String)
    resource_uri = Column(String, index=True, unique=True)

    title = Column(String)
    slug = Column(String, index=True, unique=True)
    description = Column(Text)

class Package(Base):
    __tablename__ = 'packages'
    #objects = sessionmaker(bind=engine)

    id = Column(Integer, primary_key=True)
    #created = Column(DateTime)

    categories = relationship('Category', secondary=association_table, backref='packages')

    #category_id = Column(Integer, ForeignKey('categories.id'))
    #category = relationship("Category", backref=backref('packages', order_by=id))

    title = Column(String)
    slug = Column(String, index=True, unique=True)
    description = Column(Text)

    package_name = Column(String)

    absolute_url = Column(String)
    resource_uri = Column(String, index=True, unique=True)
    usage_count = Column(Integer, index=True)

    pypi_url = Column(String)
    pypi_version = Column(Text)
    pypi_downloads = Column(Integer, index=True)

    repo_url = Column(String)
    repo_description = Column(Text)
    repo_watchers = Column(Integer, index=True)
    repo_forks = Column(Integer, index=True)
    participants = Column(Text)

    installed = Column(Boolean, index=True)
    installed_version = Column(String)

    installed_info = False

    def set_package_name(self):
        if self.pypi_package_name:
            self.package_name = self.pypi_package_name
        self.package_name = self.repo_name

    @property
    def pypi_package_name(self):
        if not self.pypi_url:
            return ''
        parsed_url = urlparse(self.pypi_url)
        if parsed_url.hostname != "pypi.python.org":
            return ''
        if not parsed_url.path.startswith("/pypi/"):
            return ''
        return parsed_url.path.split('/')[2]

    @property
    def repo_type(self):
        if not self.repo_url:
            return False
        parsed_url = urlparse(self.repo_url)
        if parsed_url.hostname == "github.com":
            return "git"
        if parsed_url.hostname == "bitbucket.com":
            return "hg"
        if parsed_url.hostname.endswith("launchpad.net"):
            return "bzr"
        return False

    @property
    def repo_name(self):
        if not self.repo_url:
            return ''
        parsed_url = urlparse(self.repo_url)
        if parsed_url.hostname == "github.com":
            # /ask/django-celery.git or /ask/django-celery/
            return parsed_url.path.split('/')[2].replace('.git','')
        if parsed_url.hostname == "bitbucket.com":
            # /offline/django-annoying
            return parsed_url.path.split('/')[2]
        if parsed_url.hostname.endswith("launchpad.net"):
            # https://code.launchpad.net/django-tables
            return parsed_url.path.split('/')[1]
        return ''

    def update_installed_info(self):
        pip_bootstrap = PIPBootstrap()
        installed_info = pip_bootstrap.check_if_installed(self.pypi_package_name or self.repo_name)
        self.installed = installed_info and True or False
        if installed_info:
            self.installed = True
            self.installed_version = installed_info._version
        else:
            self.installed = False
            self.installed_version = None

    def check_readthedocs(self):
        url = "http://readthedocs.org/api/v1/version/%s/?format=json"

    #@property
    #def check_installed(self):
    #    return {
    #        'installed': True,
    #        '_version': self.installed_version or '',
    #    }

    @property
    def install_string(self):
        if self.pypi_package_name:
            return self.pypi_package_name
        elif self.repo_type:
            return "%s+%s#" %(self.repo_type, self.repo_url, self.repo_name)
        return ''

def create_tables():
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    from sqlalchemy.sql import select

    conn = engine.connect()
    packages = Package.__table__

    query = select([packages.c.package_name], packages.c.installed==True)
    for result in conn.execute(query):
        print result


