from clint.eng import join
from clint.textui import colored, cols, progress, columns, indent, puts, puts_err

from distutils.version import LooseVersion as versioner

import sys
STREAM = sys.stderr

class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self):
        return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

class Paginator(object):

    def __init__(self, objects, pagination=10, query=None):
        self.objects = objects
        self.pagination = pagination
        self._current_page = 1
        self.query = query

    #@property
    #def objects(self):
    #    return self._objects.all()

    def refresh_objects(self):
        if self.query:
            self.objects = self.query.all()

    @property
    def num_pages(self):
        return (len(self.objects)+self.pagination-1) / self.pagination

    def page(self, num=1):
        if num < 1 or num > self.num_pages:
            raise Exception("Invalid page number")

        self._current_page = num

        start_index = (num-1)*self.pagination
        end_index = num*self.pagination
        return self.objects[start_index:end_index]

    def current_page(self):
        return self.page(self._current_page)


    def next(self):
        self._current_page += 1

    def prev(self):
        self._current_page -= 1

def listen_for_cli_command():
    return _Getch().impl()

def puts_header(text, color='green', minimal=True ):
    """
    ##############
    ### HEADER ###
    ##############
    """
    length = len(text) + 8
    color_text = getattr(colored, color)
    if minimal:
        puts(colored.green("="*80), newline=False)
        puts(color_text(text))
        puts(colored.green("="*80), newline=False)
    else:
        puts("#"*length)
        puts("### "+ color_text(text)+ " ###")
        puts("#"*length)

    puts()

def puts_key_value(key, value):
    key_column = [f'{key}:', 20]
    value_column = [value, 80]
    puts(columns(key_column, value_column) )

def adapt_text_to_column(text, size=10):
    return [text, size]

def puts_package_list(paginator, current_page, highlighted_item):



    packages = paginator.page(current_page)
    starting_index = paginator.pagination*(current_page-1)

    pagination_tpl = "Page %s of %s" %(current_page, paginator.num_pages)

    puts(colored.green('='*80), newline=False)
    puts(pagination_tpl)
    puts(colored.green('='*80))

    for index, package in enumerate(packages):
        #if package.check_installed:
        #    puts('* ' + colored.green(package.title) + ' [Installed] ' + colored.yellow(package.pypi_package_name) + ' ' + colored.yellow(package.repo_name))
        #else:
        #    puts('* ' + colored.green(package.title) + ' ' + colored.yellow(package.pypi_package_name) + ' ' + colored.yellow(package.repo_name))

        #STREAM.write(package.title+"\r\n")

        #STREAM.write("\r")

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
            "using": package.usage_count,
            "PYPI dl": package.pypi_downloads,
            #"forks": package.repo_forks,
            "watching": package.repo_watchers,
        }
        cols = [["%s: %s" %(key, value), 20] for key,value in info.items()]

        with indent(indent=6):
            #puts()
            puts(columns(*cols))

        puts()


    puts(colored.green('='*80), newline=False)
    puts(pagination_tpl)
    puts(colored.green('='*80))
