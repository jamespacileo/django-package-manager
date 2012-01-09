import tempfile

from pip import main as pip_main
from pip.util import get_installed_distributions

class PIPBootstrap(object):
    """
    PIP main returns
    0 = All good
    1 = All failed
    2 = Some failed
    """
    def __init__(self):
        pass

    def install(self, package_names):
        args = ["install", ' '.join(package_names)]
        return pip_main(args)

    def uninstall(self, package_names):
        args = ["uninstall", ' '.join(package_names)]
        return pip_main(args)

    def upgrade(self, package_names):
        args = ["install", "-U", ' '.join(package_names)]
        return pip_main(args)

    def installed_packages(self):
        return get_installed_distributions()

    def check_if_installed(self, package_name):
        installed_packages = self.installed_packages()
        for package in installed_packages:
            if package_name == package.project_name:
                return package
        return False


