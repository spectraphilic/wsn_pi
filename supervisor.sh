cat << EOF
[program:wsn_xbee]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_xbee.py
stderr_logfile=$PWD/log/wsn_xbee.err.log
stdout_logfile=$PWD/log/wsn_xbee.out.log
autostart=true
autorestart=true

[program:wsn_cook]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_cook.py
stderr_logfile=$PWD/log/wsn_cook.err.log
stdout_logfile=$PWD/log/wsn_cook.out.log
autostart=true
autorestart=true

[program:wsn_archive_raw]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_archive_raw.py
stderr_logfile=$PWD/log/wsn_archive_raw.err.log
stdout_logfile=$PWD/log/wsn_archive_raw.out.log
autostart=true
autorestart=true

[program:wsn_archive_cooked]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_archive_cooked.py
stderr_logfile=$PWD/log/wsn_archive_cooked.err.log
stdout_logfile=$PWD/log/wsn_archive_cooked.out.log
autostart=true
autorestart=true

[program:wsn_2django]
directory=$PWD
user=$USER
command=$PWD/venv/bin/python wsn_2django.py
stderr_logfile=$PWD/log/wsn_2django.err.log
stdout_logfile=$PWD/log/wsn_2django.out.log
autostart=true
autorestart=true
EOF
