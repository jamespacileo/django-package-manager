from distutils.version import LooseVersion
import os
import webbrowser
from clint.textui import colored, progress
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

from distutils.version import LooseVersion as versioner

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))

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
        puts("Category list downloaded 1/1 OK")
        #progress_bar = progress.bar(len(categories))
        for category in progress.bar(categories):

            #progress_bar.next()

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

        puts()

        puts_header("Updating packages...")
        packages = dp_bootstrap.app_list()
        puts("Package list downloaded 1/1 OK")
        for package in progress.bar(packages):
            filtered_args = [(key,val) for key,val in package.items() if key in PACKAGE_FIELDS]
            package_model = session.query(Package).filter(Package.slug==package['slug']).first()
            #print "PACKAGE_MODEL", package_model
            if package_model:
                for key, val in filtered_args:
                    setattr(package_model, key, val)
            else:
                package_model = Package(**dict(filtered_args))
                session.add(package_model)

            package_model.set_package_name()

            package_model.categories = []
            if package['grids']:
                if "/api/v1/grid/this-site/" in package['grids']:
                    package['grids'].remove("/api/v1/grid/this-site/")
                categories = session.query(Category).filter(Category.resource_uri.in_(package['grids']))
                for category in categories:
                    package_model.categories.append(category)

        session.commit()
        print "Packages updated"

        self._check_installed_packages()


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
        self.view = "menu-view"
        category = "All"

        # MENU VIEW
        self.menu_view = {
            'highlighted_item': 1,
            'options': {
                'Packages': 'main-view',
                'Categories': 'category-choice-view',
                'Virtual Environments': 'virtual-env-view',
                'Help': 'help-view',
                'Update': 'update-view',
                'About': 'about-view',
            }
        }

        self.session = Session()
        #self.session = session

        categories = self.session.query(Category).order_by(Category.title).all()
        self.category_choice_view = {
            'categories': categories,
            'paginator' : Paginator(objects=categories, pagination=10),
            'current_page' : 1,
            'highlighted_item' : 1,
            'ordering': 'name',
        }

        self.category_choice_view['category_paginator'] = Paginator(objects=categories, pagination=10)
        self.category_choice_view['current_page'] = 1
        self.category_choice_view['highlighted_item'] = 1
        self.category_choice_view['info'] = {}

        if category_name:
            category = self.session.query(Category).filter(Category.slug == category_name)
            if not category:
                category = "All"
                puts_err("Could not find specified category.")

                self.view = 'category-choice-view'


        packages_query = self.session.query(Package).order_by(Package.pypi_downloads.desc())
        packages = packages_query.all()

        puts("")


        self.main_view = {}
        self.main_view['paginator'] = Paginator(packages, pagination=10)
        self.main_view['paginator'].base_query = self.session.query(Package)
        self.main_view['current_page'] = 1
        self.main_view['highlighted_item'] = 1
        self.main_view['info'] = {
            'Category': category_name or 'All',
            'Package count': self.session.query(Package).count(),
            }
        self.main_view['ordering'] = 'downloads'

        self._render()

        while True:
            key = listen_for_cli_command()

            if key == 'q':
                quit()


            if self.view == "menu-view":
                # MAIN MENU
                if ord(key) == 80:
                    # UP key
                    if not self.menu_view['highlighted_item'] >= len(self.menu_view['options']):
                        self.menu_view['highlighted_item'] += 1

                    self._render_main_menu()

                elif ord(key) == 72:
                    # DOWN key
                    if not self.menu_view['highlighted_item'] <= 1:
                        self.menu_view['highlighted_item'] -= 1

                    self._render_main_menu()

                elif ord(key) == 13:
                    # ENTER key
                    index = self.menu_view['highlighted_item']-1
                    self.view = self.menu_view['options'].values()[index]
                    print "going to %s..." %self.view

                    self._render()

            elif self.view == "virtual-env-list-view":
                pass



            elif self.view == 'main-view':
                if   key == 'n' or ord(key) == 77:
                    # N = Next page
                    if self.main_view['current_page'] >= self.main_view['paginator'].num_pages:
                        puts_err("You are already at the last page")
                        continue

                    self.main_view['current_page'] += 1
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

                elif key == 'p' or ord(key) == 75:
                    # P = Previous page
                    if self.main_view['current_page'] <= 1:
                        puts_err("You are already at the first page")
                        continue

                    self.main_view['current_page'] -= 1
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

                elif key == 'u':
                    # SORT BY USING
                    self.main_view['ordering'] = 'people using library'
                    self.main_view['paginator'].objects = self.main_view['paginator'].base_query.order_by(Package.usage_count.desc()).all()
                    self.main_view['current_page'] = 1
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

                elif key == 'c':
                    self.view = "category-choice-view"
                    self._render_category_choice_view(self.category_choice_view['category_paginator'], self.category_choice_view['current_page'], self.main_view['info'], self.category_choice_view['highlighted_item'])


                elif key == 'g':
                    # UPDATE
                    self.view = 'update-view'
                    self.update()
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])
                    self.view = 'main-view'

                elif key == 'w':
                    # SORT BY WATCHING
                    self.main_view['ordering'] = 'people wathcing repository'
                    self.main_view['paginator'].objects = self.main_view['paginator'].base_query.order_by(Package.repo_watchers.desc()).all()
                    self.main_view['current_page'] = 1
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

                elif key == 'd':
                    # SORT by Downloads
                    self.main_view['ordering'] = 'PYPI downloads'
                    self.main_view['paginator'].objects = self.main_view['paginator'].base_query.order_by(Package.pypi_downloads.desc()).all()
                    self.main_view['current_page'] = 1
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

                elif ord(key) == 13:
                    # Pressed ENTER onto package
                    self.view = 'package-view'
                    package = self.main_view['paginator'].current_page()[self.main_view['highlighted_item']-1]
                    self._render_package_info(package)

                    rtd_bootstrap = ReadTheDocsBootstrap(proxy=self.proxy)
                    docs = rtd_bootstrap.check_if_docs_exist(package.pypi_package_name or package.repo_name)
                    if docs:
                        self._render_package_info(package, docs=docs)


                elif ord(key) == 72:
                    # pressed UP
                    if not self.main_view['highlighted_item'] <= 1:
                        self.main_view['highlighted_item'] -= 1
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

                elif ord(key) == 80:
                    # pressed DOWN
                    if not self.main_view['highlighted_item'] >= 10:
                        self.main_view['highlighted_item'] += 1
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

                elif ord(key) == 8:
                    # BACKSPACE key
                    self.view = 'menu-view'
                    self._render()

            elif self.view == 'package-view':

                if key == 'i':
                    #INSTALL
                    self.view = "install-view"

                    self._clear_screen()

                    puts(colored.magenta("Installing..."))
                    puts()

                    package = self.main_view['paginator'].current_page()[self.main_view['highlighted_item']-1]
                    result = self.install(package_names=[package.install_string])
                    if not result:
                        package.update_installed_info()
                        self.session.commit()

                    self.main_view['paginator'].refresh_objects()

                    puts()
                    puts(colored.magenta("Press ENTER to continue..."))
                    s = raw_input()

                    self.view = 'package-view'
                    self._render()
                    #self._render_package_info(package)


                elif key == 'u':
                    # UNINSTALL
                    self.view = "install-view"

                    self._clear_screen()

                    puts(colored.magenta("Uninstalling..."))
                    puts()

                    package = self.main_view['paginator'].current_page()[self.main_view['highlighted_item']-1]
                    result = self.uninstall(package_names=[package.pypi_package_name or package.repo_name])
                    if result:
                        puts(result)

                    if not result:
                        package.installed = False
                        self.session.commit()

                    self.main_view['paginator'].refresh_objects()

                    puts()
                    puts(colored.magenta("Press ENTER to continue..."))
                    s = raw_input()

                    self.view = 'package-view'
                    self._render_package_info(package)

                elif ord(key) == 8:
                    # BACKSPACE
                    self.view = 'main-view'
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

                elif key == 'p':
                    # PYPI webpage
                    package = self.main_view['paginator'].current_page()[self.main_view['highlighted_item']-1]
                    webbrowser.open(package.pypi_url)

                elif key == 'r':
                    # REPO page
                    package = self.main_view['paginator'].current_page()[self.main_view['highlighted_item']-1]
                    webbrowser.open(package.repo_url)

            elif self.view == 'installed-view':
                pass

            elif self.view == 'category-choice-view':
                if   key == 'n' or ord(key) == 77:
                    # N = Next page
                    if self.category_choice_view['current_page'] >= self.category_choice_view['category_paginator'].num_pages:
                        puts_err("You are already at the last page")
                        continue

                    self.category_choice_view['current_page'] += 1
                    self._render()
                    #self._render_category_choice_view(self.category_choice_view['category_paginator'], self.category_choice_view['current_page'], self.main_view['info'], self.category_choice_view['highlighted_item'])

                elif key == 'p' or ord(key) == 75:
                    # P = Previous page
                    if self.category_choice_view['current_page'] <= 1:
                        puts_err("You are already at the first page")
                        continue

                    self.category_choice_view['current_page'] -= 1
                    self._render()
                    #self._render_category_choice_view(self.category_choice_view['category_paginator'], self.category_choice_view['current_page'], self.main_view['info'], self.category_choice_view['highlighted_item'])

                elif ord(key) == 13:
                    # Pressed ENTER onto package

                    category = self.category_choice_view['category_paginator'].current_page()[self.category_choice_view['highlighted_item']-1]

                    packages_base_query = self.session.query(Package).filter(Package.categories.any(id=category.id))
                    self.main_view['paginator'] = Paginator(objects=packages_base_query.order_by(Package.pypi_downloads.desc()).all())
                    self.main_view['paginator'].base_query = packages_base_query

                    self.main_view['current_page'] = 1
                    self.main_view['highlighted_item'] = 1
                    self.main_view['info'] = {
                        'Category': category and category.title or 'All',
                        'Package count': len(category.packages),
                    }

                    self.view = 'main-view'
                    self._render()
                    #self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])


                elif ord(key) == 72:
                    # pressed UP
                    if not self.category_choice_view['highlighted_item'] <= 1:
                        self.category_choice_view['highlighted_item'] -= 1
                    self._render()
                    #self._render_category_choice_view(self.category_choice_view['category_paginator'], self.category_choice_view['current_page'], self.main_view['info'], self.category_choice_view['highlighted_item'])

                elif ord(key) == 80:
                    # pressed DOWN
                    if not self.category_choice_view['highlighted_item'] >= 10:
                        self.category_choice_view['highlighted_item'] += 1
                    self._render()
                    #self._render_category_choice_view(self.category_choice_view['category_paginator'], self.category_choice_view['current_page'], self.main_view['info'], self.category_choice_view['highlighted_item'])

                elif ord(key) == 8:
                    # BACKSPACE key
                    self.view = 'menu-view'
                    self._render()

                elif key == 'k':
                    # ORDERING by Package count
                    self.category_choice_view['ordering'] = 'package count'
                    #self.category_choice_view['paginator'] = self.category_choice_view['paginator'].base_query.order_by(Category.package.desc()).all()

                    self.main_view['paginator'].objects = self.main_view['paginator'].base_query.order_by(Package.usage_count.desc()).all()
                    self.main_view['current_page'] = 1
                    self._render_package_list(self.main_view['paginator'], self.main_view['current_page'], self.main_view['info'], self.main_view['highlighted_item'])

            elif self.view in ['about-view', 'help-view']:

                if ord(key) == 8:
                    self.view = "menu-view"
                    self._render()

    def _check_installed(self):
        pip_bootstrap = PIPBootstrap()
        installed_packages = pip_bootstrap.installed_packages()

    def requirements(self):
        pass

    def _render(self):
        self._clear_screen()
        if self.view == 'menu-view':
            self._render_main_menu()

        elif self.view == 'main-view':
            paginator = self.main_view['paginator']
            current_page = self.main_view['current_page']
            info = self.main_view['info']
            highlighted_item = self.main_view['highlighted_item']

            self._render_package_list(paginator, current_page, info, highlighted_item)

        elif self.view == 'category-choice-view':
            paginator = self.category_choice_view['paginator']
            info = self.main_view['info']
            current_page = self.category_choice_view['current_page']
            highlighted_item = self.category_choice_view['highlighted_item']

            self._render_category_choice_view(paginator, current_page, info, highlighted_item)

        elif self.view == 'update-view':
            self.update()
            self.view = 'menu-view'
            self._render()

        elif self.view == 'package-view':
            package = self.main_view['paginator'].current_page()[self.main_view['highlighted_item']-1]
            self._render_package_info(package)

            rtd_bootstrap = ReadTheDocsBootstrap(proxy=self.proxy)
            if docs := rtd_bootstrap.check_if_docs_exist(
                package.pypi_package_name or package.repo_name
            ):
                self._render_package_info(package, docs=docs)

        elif self.view == 'about-view':

            with open(os.path.join(PROJECT_DIR, 'templates', 'ABOUT.txt')) as file:
                puts(file.read())
        elif self.view == 'help-view':

            with open(os.path.join(PROJECT_DIR, 'templates', 'HELP.txt')) as file:
                puts(file.read())




    def _render_main_menu(self):
        self._clear_screen()
        #puts_header("Django Package Manager")

        ascii_art = """\
 ___     _   ___         _
|   \ _ | | | _ \__ _ __| |____ _ __ _ ___
| |) | || | |  _/ _` / _| / / _` / _` / -_)
|___/ \__/  |_| \__,_\__|_\_\__,_\__, \___|
                                 |___/
 __  __
|  \/  |__ _ _ _  __ _ __ _ ___ _ _
| |\/| / _` | ' \/ _` / _` / -_) '_|
|_|  |_\__,_|_||_\__,_\__, \___|_|
                      |___/         """

        with indent(indent=4):
            puts(colored.green(ascii_art))

        puts(colored.green("="*80), newline=False)
        puts("    Main menu")
        puts(colored.green("="*80))


        for index, option in enumerate(self.menu_view['options'].keys()):
            quote = "  * " if self.menu_view['highlighted_item'] == index+1 else ""
            with indent(indent=4, quote=quote):
                puts(option)
            puts()

        puts(colored.green("="*80))

        with indent(indent=4):
            puts("https://github.com/jamespacileo/django-package-manager")

    def _render_package_list(self, paginator, current_page, info, highlighted_item):
        self._clear_screen()

        puts_header("Listing packages")
        for key,val in info.items():
            if key == 'Category':
                puts_key_value(key, colored.magenta(str(val)))
            else:
                puts_key_value(key, str(val))

        puts(colored.green("-"*80))

        #puts_key_value("Main categories", "[A]ll, [I]nstalled")
        puts_key_value("Order by","Na[m]e, [I]nstalled, [U]sage, [W]atchers")


        packages = paginator.page(current_page)
        starting_index = paginator.pagination*(current_page-1)

        pagination_tpl = "Page " + colored.yellow("%s" %current_page) + " of %s" %paginator.num_pages

        if self.main_view.get('ordering'):
            pagination_tpl += " - Ordering by: " + colored.yellow(self.main_view.get('ordering'))

        puts(colored.green('-'*80), newline=False)
        puts(pagination_tpl)
        puts(colored.green('-'*80))

        for index, package in enumerate(packages):

            with indent(indent=6, quote="%s)" %str(starting_index+index+1)):
                title = colored.green(package.title)

                if index+1 == highlighted_item:
                    title = f' * {title}'


                if package.installed:
                    if not package.installed_version:
                        # There is no package version! We can't deduce if a new version is really available.
                        title += colored.yellow(" [Installed] ")
                    else:
                        # Package version is there. Everything normal and good!
                        title += colored.yellow(" [Installed %s] " %package.installed_version)
                        if versioner(package.installed_version) < versioner(package.pypi_version):
                            title += colored.red(" [New version %s] " %package.pypi_version)
                puts(title)

            info = {
                "downloads": package.pypi_downloads,
                #"forks": package.repo_forks,
                "watching": package.repo_watchers,
                "using": package.usage_count,
                }
            cols = [[colored.white("%s %s" %(value, key)), 20] for key,value in info.items()]

            with indent(indent=6):
                #puts()
                puts(columns(*cols))

            puts()


        puts(colored.green('-'*80), newline=False)
        puts(pagination_tpl)
        puts(colored.green('-'*80))

        #puts_package_list(paginator, current_page, highlighted_item)

    def _render_category_choice_view(self, paginator, current_page, info, highlighted_item):
        self._clear_screen()

        puts_header("Choose a category")

        puts_key_value("Current category", colored.yellow(info['Category']))

        puts(colored.green("-"*80))

        puts_key_value("Main categories", "[A]ll, [I]nstalled")
        puts_key_value("Order by","Na[m]e, Pac[K]ages")


        categories = paginator.page(current_page)
        starting_index = paginator.pagination*(current_page-1)

        pagination_tpl = "Page %s of %s" %(current_page, paginator.num_pages)

        puts(colored.green("-"*80), newline=False)
        puts(pagination_tpl)
        puts(colored.green("-"*80))

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

        puts(colored.green("-"*80), newline=False)
        puts(pagination_tpl)
        puts(colored.green("-"*80))

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

        puts("Checking installed packages")

        for installed_package in progress.bar(installed_packages):
            name = installed_package.project_name

            if (
                package := self.session.query(Package)
                .filter(Package.package_name == name)
                .first()
            ):
                package.installed = True
                package.installed_version = installed_package._version

            self.session.commit()


    def update_database(self):
        # check for document urls !CAN TAKE TIME
        # check for new packages in database !CAN TAKE TIME

        pass

    def _clear_screen(self):
        if os.system("cls"): # WINDOWS
            os.system("clear") # UNIX


