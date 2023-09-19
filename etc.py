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

supervisor_header = f"""[supervisord]
pidfile = {cwd}/var/run/supervisord.pid
logfile = {cwd}/var/log/supervisord.log

[unix_http_server]
file = {cwd}/var/run/supervisord.socket

[supervisorctl]
serverurl = unix://{cwd}/var/run/supervisord.socket

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

"""

supervisor_program = f"""[program:{{name}}]
command={sys.executable} %(program_name)s.py
directory={cwd}
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

def write_supervisor(file):

    for name in config_parser.sections():
        section = dict(config_parser[name])
        if name in programs:
            data = defaults.copy()
            data['name'] = name
            data.update(programs[name])
            data.update(section)
            file.write(supervisor_program.format(**data))
            file.write('\n')
        else:
            file.write(f'[{name}]\n')
            for key, value in section.items():
                file.write(f'{key} = {value}\n')
            file.write('\n')


service_template = f"""[Unit]
Description=WSN Pi
After=rabbitmq-server.service
Wants=rabbitmq-server.service

[Service]
ExecReload=/bin/kill -SIGHUP $MAINPID
ExecStart={cwd}/venv/bin/supervisord -c {cwd}/var/supervisor.conf -n
KillSignal=TERM
Restart=on-failure
User={user}
WorkingDirectory={cwd}

[Install]
WantedBy=multi-user.target
"""

if __name__ == '__main__':
    config_parser = ConfigParser()
    config_parser.read('config.ini')

    with open('var/supervisor.conf', 'w') as file:
        file.write(supervisor_header)
        write_supervisor(file)

    with open('var/wsn-pi.service', 'w') as file:
        file.write(service_template)
