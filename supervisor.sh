cat << EOF
[program:wsn_xbee]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_xbee.py
stderr_logfile=$PWD/log/wsn_xbee.err.log
stdout_logfile=$PWD/log/wsn_xbee.out.log
autostart=true
startsecs=3
startretries=20
autorestart=true

[program:wsn_raw_archive]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_raw_archive.py
stderr_logfile=$PWD/log/wsn_raw_archive.err.log
stdout_logfile=$PWD/log/wsn_raw_archive.out.log
autostart=true
startsecs=3
startretries=20
autorestart=true

[program:wsn_raw_cook]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_raw_cook.py
stderr_logfile=$PWD/log/wsn_raw_cook.err.log
stdout_logfile=$PWD/log/wsn_raw_cook.out.log
autostart=true
startsecs=3
startretries=20
autorestart=true

[program:wsn_data_archive]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_data_archive.py
stderr_logfile=$PWD/log/wsn_data_archive.err.log
stdout_logfile=$PWD/log/wsn_data_archive.out.log
autostart=true
startsecs=3
startretries=20
autorestart=true

[program:wsn_data_django]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_data_django.py
stderr_logfile=$PWD/log/wsn_data_django.err.log
stdout_logfile=$PWD/log/wsn_data_django.out.log
autostart=true
startsecs=3
startretries=20
autorestart=true
EOF
