#!/usr/bin/python3

from setuptools import setup
import os
if os.path.exists("./version.txt"):
    with open ("./version.txt") as version_file:
        version = version_file.read()
else:
    ## Use latest hardcoded version
    version="1.0.5"

try:
    setup(
        name="remote-media-controller",
        version=version,
        packages=[],
        install_requires=["PySimpleGUI"],
        url="https://github.com/le-firehawk/remote-media-controller",
        license="AGPL v3",
        author="le-firehawk",
        author_email="firehawk@opayq.net",
        description="Python-based SSH or CMUS-remote media controller"
    )
except Exception as e:
    print(e)
    exit()
else:
    print("Installation successful!")
    print("If running in CMUS mode, the cmus package, which ships cmus-remote utility, must be installed on both hosts")
    print("If running in SSH/PlayerCTL mode, the playerctl package must be installed on the destination host, and ssh on the source host")
