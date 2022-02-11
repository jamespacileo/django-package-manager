import tempfile
import os

from pip import main as pip_main
from pip.util import get_installed_distributions

class PIPBootstrap(object):
    """
    PIP main returns
    0 = All good
    1 = All failed
    2 = Some failed
    """
    def __init__(self, proxy=""):
        self.proxy = proxy
        #self.pip_folder = os.path.abspath(os.path.dirname(pip_main))
        #self.pip_bin = os.path.join(self.pip_folder, '__init__.py')

    def build_args(self, command, *args):
        pip_args = [command]
        if self.proxy:
            pip_args.extend(['--proxy', self.proxy])
        pip_args.extend(args)
        return pip_args

    def install(self, package_names):
        args = self.build_args("install", *package_names)
        return os.system("pip " + ' '.join(args))
        #return pip_main(args)

    def uninstall(self, package_names):
        args = self.build_args("uninstall", *package_names)
        return os.system("pip " + ' '.join(args))
        #return pip_main(args)

    def upgrade(self, package_names):
        args = self.build_args("install", "-U", *package_names)
        return os.system("pip " + ' '.join(args))
        #return pip_main(args)

    def installed_packages(self):
        return get_installed_distributions()

    def check_if_installed(self, package_name):
        installed_packages = self.installed_packages()
        return next(
            (
                package
                for package in installed_packages
                if package_name == package.project_name
            ),
            False,
        )


