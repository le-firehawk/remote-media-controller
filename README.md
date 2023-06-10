# remote-media-controller
Python-based SSH or CMUS-remote media controller

Utilize CMUS' remote control, or playerctl's utilities via SSH to manage media playback

## Usage:
    main.py [<option>...]
e.g.
    main.py --mode ssh --ip 192.168.0.2 --port 22 --user user
### Options:
    -m, --mode      [e.g. ssh]
    -h, --ip        [e.g. 192.168.0.2]
    -P, --port      [e.g. 22]
    -u, --user      [e.g. user]
    -p, --password  [e.g. password]
