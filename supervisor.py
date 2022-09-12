# Standard Library
from configparser import RawConfigParser as ConfigParser
import getpass
import os
import sys


cwd = os.getcwd()
user = getpass.getuser()

# The program changes to the RUNNING state after <startsecs> seconds. If it
# exits before supervisor will try to start it again up to <startretries>
# times.

template = f"""[program:{{name}}]
command={sys.executable} %(program_name)s.py
directory={cwd}
user={user}
autostart={{autostart}}
startsecs=3
startretries=20
priority={{priority}}
stderr_logfile={cwd}/log/%(program_name)s.err.log
stdout_logfile={cwd}/log/%(program_name)s.out.log
"""

defaults = {
    'autostart': 'true',
}

programs = {
    'wsn_lora': {'priority': 1},
    'wsn_usb': {'priority': 1},
    'wsn_xbee': {'priority': 1},
    'wsn_raw_archive': {'priority': 2},
    'wsn_raw_cook': {'priority': 2},
    'wsn_data_archive': {'priority': 3},
    'wsn_data_django': {'priority': 3},
}


if __name__ == '__main__':
    config_parser = ConfigParser()
    config_parser.read('config.ini')

    for name in config_parser.sections():
        section = dict(config_parser[name])
        if name in programs:
            data = defaults.copy()
            data['name'] = name
            data.update(programs[name])
            data.update(section)
            print(template.format(**data))
        else:
            print(f'[{name}]')
            for key, value in section.items():
                print(f'{key} = {value}')
            print()
