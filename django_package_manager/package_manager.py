import os
import webbrowser
from clint.textui import colored
from clint.textui.cols import columns
from clint.textui.core import puts, puts_err, indent
import time

PACKAGE_DIR = os.path.abspath(os.path.dirname(__file__))

from django_package_manager.django_packages_api import DjangoPackagesBootstrap
from django_package_manager.pip_bootstrap import PIPBootstrap
from django_package_manager.models import create_tables, Category, Package, Session
from django_package_manager.cli_utils import puts_header, puts_key_value, puts_package_list, listen_for_cli_command, Paginator
from django_package_manager.readthedocs_api import ReadTheDocsBootstrap
from sqlalchemy.sql import exists

CATEGORY_FIELDS = [
                  'id',
                  'title',
                  'slug',
                  'description',
                  'absolute_url',
                  'resource_uri']

PACKAGE_FIELDS = [#'grids',
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

PROXY = None

class PackageManager(object):

    def __init__(self, proxy):
        self.proxy = proxy
        create_tables()

    def update(self):
        """
        - Download new package list
        - Update locally loaded packages
        """

        dp_bootstrap = DjangoPackagesBootstrap(proxy=self.proxy)
        session = Session()

        puts_header("Updating categories...")
        categories = dp_bootstrap.grid_list()
        for category in categories:
            filtered_args = [(key,val) for key,val in category.items() if key in CATEGORY_FIELDS]
            category_model = session.query(Category).filter(Category.slug==category['slug']).first()
            if category_model:
                for key, val in filtered_args:
                    setattr(category_model, key, val)
            else:
                category_model = Category(**dict(filtered_args))
                session.add(category_model)
        session.commit()
        print "Categories updated"

        puts_header("Updating packages...")
        packages = dp_bootstrap.app_list()
        for package in packages:
            filtered_args = [(key,val) for key,val in package.items() if key in PACKAGE_FIELDS]
            package_model = session.query(Package).filter(Package.slug==package['slug']).first()
            #print "PACKAGE_MODEL", package_model
            if package_model:
                for key, val in filtered_args:
                    setattr(package_model, key, val)
            else:
                package_model = Package(**dict(filtered_args))
                session.add(package_model)

            package_model.categories = []
            if package['grids']:
                if "/api/v1/grid/this-site/" in package['grids']:
                    package['grids'].remove("/api/v1/grid/this-site/")
                categories = session.query(Category).filter(Category.resource_uri.in_(package['grids']))
                for category in categories:
                    package_model.categories.append(category)

        session.commit()
        print "Packages updated"


    def search(self, text):
        pass

    def install(self, package_names):
        pip = PIPBootstrap(proxy=self.proxy)
        result = pip.install(package_names)

    def upgrade(self, package_names, from_repository=False):
        pip = PIPBootstrap(proxy=self.proxy)
        result = pip.upgrade(package_names)

    def uninstall(self, package_names):
        pip = PIPBootstrap(proxy=self.proxy)
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
        category = "All"

        session = Session()
        self.session = session

        categories = session.query(Category).order_by(Category.title).all()
        category_paginator = Paginator(objects=categories, pagination=10)
        category_current_page = 1
        category_highlighted_item = 1

        if category_name:
            category = session.query(Category).filter(Category.slug == category_name)
            if not category:
                category = "All"
                puts_err("Could not find specified category.")

                view = 'category-choice-view'


        packages_query = session.query(Package).order_by(Package.pypi_downloads.desc())
        packages = packages_query.all()

        puts("")

        info = {
            'Category': category_name or 'All',
            'Package count': session.query(Package).count(),
        }

        paginator = Paginator(packages, pagination=10)
        paginator.base_query = session.query(Package)
        current_page = 1
        highlighted_item = 1

        if view == 'main-view':
            self._render_package_list(paginator, current_page, info, highlighted_item)
        elif view == 'category-choice-view':
            self._render_category_choice_view(category_paginator, category_current_page, info, category_highlighted_item)

        while True:
            key = listen_for_cli_command()

            if key == 'q':
                quit()


            if view == "menu-view":
                # MAIN MENU
                pass
            elif view == "virtual-env-list-view":
                pass



            elif view == 'main-view':
                if   key == 'n' or ord(key) == 77:
                    # N = Next page
                    if current_page >= paginator.num_pages:
                        puts_err("You are already at the last page")
                        continue

                    current_page += 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'p' or ord(key) == 75:
                    # P = Previous page
                    if current_page <= 1:
                        puts_err("You are already at the first page")
                        continue

                    current_page -= 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'u':
                    # SORT BY USING
                    paginator.objects = paginator.base_query.order_by(Package.usage_count.desc()).all()
                    current_page = 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'c':
                    view = "category-choice-view"
                    self._render_category_choice_view(category_paginator, category_current_page, info, category_highlighted_item)


                elif key == 'g':
                    # UPDATE
                    view = 'update-view'
                    self.update()
                    self._render_package_list(paginator, current_page, info, highlighted_item)
                    view = 'main-view'

                elif key == 'w':
                    # SORT BY WATCHING
                    paginator.objects = paginator.base_query.order_by(Package.repo_watchers.desc()).all()
                    current_page = 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'd':
                    # SORT by Downloads
                    paginator.objects = paginator.base_query.order_by(Package.pypi_downloads.desc()).all()
                    current_page = 1
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif ord(key) == 13:
                    # Pressed ENTER onto package
                    view = 'package-view'
                    package = paginator.current_page()[highlighted_item-1]
                    self._render_package_info(package)

                    rtd_bootstrap = ReadTheDocsBootstrap(proxy=self.proxy)
                    docs = rtd_bootstrap.check_if_docs_exist(package.pypi_package_name or package.repo_name)
                    if docs:
                        self._render_package_info(package, docs=docs)


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
                    #INSTALL
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
                    # UNINSTALL
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
                    # BACKSPACE
                    view = 'main-view'
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                elif key == 'p':
                    # PYPI webpage
                    package = paginator.current_page()[highlighted_item-1]
                    webbrowser.open(package.pypi_url)

                elif key == 'r':
                    # REPO page
                    package = paginator.current_page()[highlighted_item-1]
                    webbrowser.open(package.repo_url)

            elif view == 'installed-view':
                pass

            elif view == 'category-choice-view':
                if   key == 'n' or ord(key) == 77:
                    # N = Next page
                    if category_current_page >= category_paginator.num_pages:
                        puts_err("You are already at the last page")
                        continue

                    category_current_page += 1
                    self._render_category_choice_view(category_paginator, category_current_page, info, category_highlighted_item)

                elif key == 'p' or ord(key) == 75:
                    # P = Previous page
                    if category_current_page <= 1:
                        puts_err("You are already at the first page")
                        continue

                    category_current_page -= 1
                    self._render_category_choice_view(category_paginator, category_current_page, info, category_highlighted_item)

                elif ord(key) == 13:
                    # Pressed ENTER onto package

                    category = category_paginator.current_page()[category_highlighted_item-1]

                    packages_base_query = session.query(Package).filter(Package.categories.any(id=category.id))
                    paginator = Paginator(objects=packages_base_query.order_by(Package.pypi_downloads.desc()).all())
                    paginator.base_query = packages_base_query

                    current_page = 1
                    highlighted_item = 1
                    info = {
                        'Category': category and category.title or 'All',
                        'Package count': len(category.packages),
                    }
                    self._render_package_list(paginator, current_page, info, highlighted_item)

                    view = 'main-view'

                elif ord(key) == 72:
                    # pressed UP
                    if not category_highlighted_item <= 1:
                        category_highlighted_item -= 1
                    self._render_category_choice_view(category_paginator, category_current_page, info, category_highlighted_item)

                elif ord(key) == 80:
                    # pressed DOWN
                    if not category_highlighted_item >= 10:
                        category_highlighted_item += 1
                    self._render_category_choice_view(category_paginator, category_current_page, info, category_highlighted_item)

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

    def _render_category_choice_view(self, paginator, current_page, info, highlighted_item):
        self._clear_screen()

        puts_header("Choose a category")

        puts_key_value("Current category", colored.yellow(info['Category']))

        categories = paginator.page(current_page)
        starting_index = paginator.pagination*(current_page-1)

        pagination_tpl = "Page %s of %s" %(current_page, paginator.num_pages)

        puts('-'*80, newline=False)
        puts(pagination_tpl)
        puts('-'*80)

        for index, category in enumerate(categories):

            quote = "%s)" %str(starting_index+index+1)
            if index+1 == highlighted_item:
                quote += " * "

            with indent(indent=6, quote=quote):
                title = colored.green(category.title)

                #title += "[%s]" %len(category.packages)

                puts(columns([title, 40], [colored.yellow("[%s packages]" %len(category.packages)), 40]), newline=False)

            #puts("%s" %category.description or "")

            puts()

            #with indent(indent=6):
            #    puts_key_value("Packages", "%s" %len(category.packages))
                #puts("%s" %category.description)

        puts('-'*80, newline=False)
        puts(pagination_tpl)
        puts('-'*80)

    def _render_package_info(self, package, docs=None):
        # CLEAR CLI
        self._clear_screen()

        puts_header("Package information")

        puts_key_value("Package name", colored.yellow( package.title))
        puts_key_value("Latest version", colored.yellow( package.pypi_version))
        puts_key_value("Repo url", colored.yellow( package.repo_url))
        puts_key_value("PYPI url", colored.yellow( package.pypi_url))
        if package.installed:
            puts_key_value("Installed version", colored.yellow( package.installed_version or "N\A" ))
        puts_key_value("Categories", colored.yellow( ', '.join([category.title for category in package.categories]) ))
        if docs:
            puts_key_value("ReadTheDocs", colored.magenta( docs ))
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
        puts("[p] open pypi page")
        if docs:
            puts("[d] open docs page")
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

    def _check_installed_packages(self):
        pip_bootstrap = PIPBootstrap()
        installed_packages = pip_bootstrap.installed_packages()
        for installed_package in installed_packages:
            name = installed_package.project_name


    def update_database(self):
        # check for document urls !CAN TAKE TIME
        # check for new packages in database !CAN TAKE TIME

        pass

    def _clear_screen(self):
        if os.system("cls"): # WINDOWS
            os.system("clear") # UNIX


