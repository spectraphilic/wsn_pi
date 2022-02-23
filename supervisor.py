# Standard Library
import getpass
import os

# Project
import utils


cwd = os.getcwd()
user = getpass.getuser()

# The program changes to the RUNNING state after <startsecs> seconds. If it
# exits before supervisor will try to start it again up to <startretries>
# times.

template = f"""[program:{{name}}]
command={cwd}/venv/bin/python %(program_name)s.py
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

programs = [
    {'name': 'wsn_lora', 'priority': 1},
    {'name': 'wsn_usb', 'priority': 1},
    {'name': 'wsn_xbee', 'priority': 1},
    {'name': 'wsn_raw_archive', 'priority': 2},
    {'name': 'wsn_raw_cook', 'priority': 2},
    {'name': 'wsn_data_archive', 'priority': 3},
    {'name': 'wsn_data_django', 'priority': 3},
]


if __name__ == '__main__':
    for program in programs:
        config = utils.get_config(program['name'])
        if config is not None:
            data = defaults.copy()
            data.update(program)
            data.update(config)
            print(template.format(**data))
