import os
from clint.textui import colored
from clint.textui.core import puts, puts_err
import time

PACKAGE_DIR = os.path.abspath(os.path.dirname(__file__))

from django_package_manager.django_packages_api import DjangoPackagesBootstrap
from django_package_manager.pip_bootstrap import PIPBootstrap
from django_package_manager.models import create_tables, Category, Package, Session
from django_package_manager.cli_utils import puts_header, puts_key_value, puts_package_list, listen_for_cli_command, Paginator

PACKAGE_FIELDS = [
                  'id',
                  'title',
                  'slug',
                  'description',
                  'absolute_url',
                  'resource_uri']

CATEGORY_FIELDS = [#'grids',
                  'repo_watchers',
                  'id',
                  #'category',
                  'title',
                  #'commits_over_52',
                  #'created_by',
                  #'repo_commits',
                  'participants',
                  'usage_count',
                  'pypi_url',
                  'repo_url',
                  'repo_forks',
                  'slug',
                  'repo_description',
                  'pypi_version',
                  #'created',
                  'absolute_url',
                  #'modified',
                  #'last_modified_by',
                  'pypi_downloads',
                  'resource_uri']

class PackageManager(object):

    def __init__(self):
        create_tables()

    def update(self):
        """
        - Download new package list
        - Update locally loaded packages
        """
        puts_header("Updating packages")
        dp_bootstrap = DjangoPackagesBootstrap()
        packages = dp_bootstrap.app_list()

        session = Session()
        for package in packages:
            filtered_args = [(key,val) for key,val in package.items() if key in PACKAGE_FIELDS]
            package_model = Package(**dict(filtered_args))
            session.add(package_model)
        session.commit()
        print "Packages updated"

        categories = dp_bootstrap.grid_list()
        for category in categories:
            filtered_args = [(key,val) for key,val in category.items() if key in CATEGORY_FIELDS]
            category_model = Category(**dict(filtered_args))
            session.add(category_model)
        session.commit()
        print "Categories updated"

    def search(self, text):
        pass

    def install(self, package_names):
        pip = PIPBootstrap()
        result = pip.install(package_names)

    def upgrade(self, package_names, from_repository=False):
        pip = PIPBootstrap()
        result = pip.upgrade(package_names)

    def uninstall(self, package_names):
        pip = PIPBootstrap()
        result = pip.uninstall(package_names)

    def categories(self, category):
        pass

    def packages(self, category_name=None):
        """
        Commands

        n = next page
        p = prev page
        q = quit

        """
        view = "main-view"

        session = Session()
        packages_query = session.query(Package).order_by(Package.usage_count.desc())
        packages = packages_query.all()

        puts("")

        info = {
            'Category': category_name or 'All',
            'Package count': session.query(Package).count(),
        }
        puts_header("Listing packages")

        for key,val in info.items():
            puts_key_value(key, str(val))

        paginator = Paginator(packages, pagination=10)
        current_page = 1
        highlighted_item = 1

        puts_package_list(paginator, current_page, highlighted_item)

        while True:
            key = listen_for_cli_command()

            if key == 'q':
                quit()

            if view == 'main-view':
                if   key == 'n':
                    # N = Next page
                    if current_page >= paginator.num_pages:
                        puts_err("You are already at the last page")
                        continue

                    current_page += 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'p':
                    # P = Previous page
                    if current_page <= 1:
                        puts_err("You are already at the first page")
                        continue

                    current_page -= 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'u':
                    # SORT BY USING
                    paginator.query = session.query(Package).order_by(Package.usage_count.desc())
                    current_page = 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'i':
                    pass

                elif key == 'w':
                    # SORT BY WATCHING
                    paginator.query = session.query(Package).order_by(Package.repo_watchers.desc())
                    current_page = 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'd':
                    # SORT by Downloads
                    paginator.query = session.query(Package).order_by(Package.pypi_downloads.desc())
                    current_page = 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif ord(key) == 13:
                    # Pressed ENTER onto package
                    view = 'package-view'
                    package = paginator.current_page()[highlighted_item-1]
                    self._render_package_info(package)

                elif ord(key) == 72:
                    # pressed UP
                    if not highlighted_item <= 1:
                        highlighted_item -= 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif ord(key) == 80:
                    # pressed DOWN
                    if not highlighted_item >= 10:
                        highlighted_item += 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

            elif view == 'package-view':

                if key == 'i':
                    view = "install-view"

                    self._clear_screen()

                    puts(colored.magenta("Installing..."))
                    puts()

                    package = paginator.current_page()[highlighted_item-1]
                    result = self.install(package_names=[package.install_string])
                    if not result:
                        package.update_installed_info()
                        session.commit()

                    paginator.refresh_objects()

                    puts()
                    puts(colored.magenta("Press ENTER to continue..."))
                    s = raw_input()
                    self._render_package_info(package)
                    view = 'package-view'

                elif key == 'u':
                    view = "install-view"

                    self._clear_screen()

                    puts(colored.magenta("Uninstalling..."))
                    puts()

                    package = paginator.current_page()[highlighted_item-1]
                    result = self.uninstall(package_names=[package.pypi_package_name or package.repo_name])
                    if result:
                        puts(result)

                    if not result:
                        package.installed = False
                        session.commit()

                    paginator.refresh_objects()

                    puts()
                    puts(colored.magenta("Press ENTER to continue..."))
                    s = raw_input()
                    self._render_package_info(package)
                    view = 'package-view'

                elif ord(key) == 8:
                    view = 'main-view'
                    self._render_package_list(paginator, current_page, info, highlighted_item)

            elif view == 'installed-view':
                pass


    def _check_installed(self):
        pip_bootstrap = PIPBootstrap()
        installed_packages = pip_bootstrap.installed_packages()

        for installed_package in installed_packages:
            pass

    def requirements(self):
        pass

    def _render_package_list(self, paginator, current_page, info, highlighted_item):
        self._clear_screen()

        puts_header("Listing packages")
        for key,val in info.items():
            puts_key_value(key, str(val))

        puts_package_list(paginator, current_page, highlighted_item)

    def _render_package_info(self, package):
        # CLEAR CLI
        self._clear_screen()

        puts_header("Package information")

        puts_key_value("Package name", colored.yellow( package.title))
        puts_key_value("Latest version", colored.yellow( package.pypi_version))
        puts_key_value("Repo url", colored.yellow( package.repo_url))
        puts_key_value("PYPI url", colored.yellow( package.pypi_url))
        if package.installed:
            puts_key_value("Installed version", colored.yellow( package.installed_version or "N\A" ))

        # DESCRIPTION

        puts('-'*80, newline=False)
        puts("Description:")
        puts()
        puts(colored.yellow( package.repo_description))
        puts('-'*80)

        # COMMANDS
        puts("Commands:")
        puts()
        if not package.installed:
            puts("[i] install")
        else:
            puts("[o] upgrade install")
            puts("[u] uninstall")
        puts()
        puts("[d] open docs")
        puts("[r] open repository url")
        puts()
        puts("[backspace] return to previous screen")

    def refresh_database(self):

        # check for installed packages, update installed package info
        session = Session()
        packages = session.query(Package).order_by(Package.usage_count.desc()).all()
        for package in packages:
            package.check_installed()
        session.commit()

    def update_database(self):
        # check for document urls !CAN TAKE TIME
        # check for new packages in database !CAN TAKE TIME

        pass

    def _clear_screen(self):
        if os.system("cls"): # WINDOWS
            os.system("clear") # UNIX

