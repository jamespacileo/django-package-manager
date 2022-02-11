import sys
import os

sys.path.insert(0, os.path.abspath('..'))

from clint.textui import puts, colored, indent, progress
from clint import args

from django_package_manager import PackageManager

if __name__=="__main__":




    #with indent(4, quote='>>>'):
    #    puts(colored.red('Aruments passed in: ') + str(args.all))
    #    puts(colored.red('Flags detected: ') + str(args.flags))
    #    puts(colored.red('Files detected: ') + str(args.files))
    #    puts(colored.red('NOT Files detected: ') + str(args.not_files))
    #    puts(colored.red('Grouped Arguments: ') + str(dict(args.grouped)))

    grouped_args = dict(args.grouped)

    proxy = grouped_args['--proxy'][0] if grouped_args.has_key('--proxy') else None
    pm = PackageManager(proxy=proxy)

    if grouped_args['_'][0] == 'update':
        pm.update()
    elif grouped_args['_'][0] == 'list':
        pm.packages()