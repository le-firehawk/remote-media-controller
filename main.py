#!/usr/bin/python3

# Copyright (C) 2023 le-firehawk

# remote-media-controller is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# remote-media-controller is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# To contact the owner of remote-media-controller, use the following:
# Email: firehawk@opayq.net

# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/agpl-3.0.html>

import PySimpleGUI as gui
import subprocess, re, sys, os, hashlib

# TODO: Read theme from file
gui.theme("black")

class controller:
    def __init__(self, parameters, version):
        self.__version__ = version

        # TODO: Add IPv6 regex + general IPv6 support
        self.ipv4_pattern = re.compile("[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}")
        self.ipv6_pattern = None
        ## Pre-define PySimpleGUI output variables for while loop in __openWindow__()
        self.__event__, self.__values__ = True, ""

        ## Dictionary of unicode symbols (only include alterable through GUI)
        self.__unicode_symbols__ = {"repeat_playlist": "🔁", "repeat_track": "🔂", "repeat_none": "🠂"}

        ## Load parameters
        self.__remoteHost__ = parameters.get("remoteHost", None)
        self.__remoteHostPort__ = parameters.get("remotePort", None)
        self.__remoteHostUser__ = parameters.get("remoteUser", None)
        self.__remoteHostPassword__ = parameters.get("password", None)
        self.__mode__ = parameters.get("mode", "cmus")

        ## Default seek duration is 5 seconds
        self.__seekDuration__, self.__playbackVolume__ = "5S", 100

        ## Repeat is assumed to be playlist
        # NOTE: Many media players do not respect playerctl's loop instructions
        # NOTE: hence, only 'track' is an effective repeat state
        self.__repeatState__, self.__playState__, self.__shuffleState__ = "playlist", "paused", True

        self.__fetchMetadata__(include_volume=True, include_play_state=True, include_playback_controls=True)
        self.__openWindow__()

    def __openWindow__(self):
        self.__layout__ = [
            [
                gui.Text("IP Address: "),
                gui.InputText(key="remoteIPaddress", default_text=self.__remoteHost__, size=(10,5)),
                gui.Button("🔄", key="refresh_metadata", tooltip="Refresh Metadata")
            ], [
                gui.Text(self.__metadata__.get("title", "Unknown Track"), key="current_title", size=(25,2))
            ], [
                gui.Text(self.__metadata__.get("artist", "Unknown Artist"), key="current_artist", size=(25,2))
            ], [
                gui.Text(self.__metadata__.get("album", "Unknown Album"), key="current_album", size=(25,2))
            ], [
                gui.Button("🔀", key="shuffle_toggle", tooltip=f"Shuffle: {str(self.__shuffleState__).replace('True', 'On').replace('False', 'Off')}"),
                gui.Button(self.__unicode_symbols__[f"repeat_{self.__repeatState__.lower()}"], key="repeat_toggle", tooltip=f"Repeat: {self.__repeatState__.capitalize()}"),
                gui.Button("⏮︎", key="previous", tooltip="Previous Track"),
                gui.Button("⏪︎", key="seek_back", tooltip="Seek Backwards"),
                ## Alternate text/background colors to indicate when playback is active
                gui.Button("⏯︎", key="play_pause", bind_return_key=True, button_color=("white", "black") if self.__playState__.lower().strip() == "playing" else ("black", "white"), tooltip="Play/Pause"),
                gui.Button("⏩︎", key="seek_forward", tooltip="Seek Forwards"),
                gui.Button("⏭︎", key="next", tooltip="Next Track")
            ], [
                gui.Image(self.__metadata__.get("image", "default.png"), size=(384,384), key="current_image"),
                gui.Slider(range=(0,100), key="volume_control", orientation="v", default_value=self.__playbackVolume__)
            ], [
                self.__generateCopyrightElement__()
            ]
        ]

        window = gui.Window(
            title="Remote Media Controller",
            layout=self.__layout__,
            margins=(100, 50),
            font="Courier 30",
            finalize=True
        )

        ## Update client each time volume is updated
        window["volume_control"].bind('<ButtonRelease-1>', "-update")

        while self.__event__:
            self.__event__, self.__values__ = window.read()

            if self.__event__ == "volume_control-update":
                ## Changing volume does not trigger any actions for other events
                self.__updatePlaybackVolume__(int(self.__values__.get("volume_control", self.__playbackVolume__)))
            elif self.__event__ == "refresh_metadata":
                self.__fetchMetadata__(include_volume=True, include_play_state=True)
                ## Update playback information
                window["current_title"].update(self.__metadata__.get("title", "Unknown Track"))
                window["current_artist"].update(self.__metadata__.get("artist", "Unknown Track"))
                window["current_album"].update(self.__metadata__.get("album", "Unknown Track"))
                window["current_image"].update(self.__metadata__.get("image", "Unknown Track"))
                window["volume_control"].update(self.__playbackVolume__)
            elif self.__event__ == "repeat_toggle":
                if self.__repeatState__ == "playlist":
                    self.__repeatState__ = "track"
                elif self.__repeatState__ == "track":
                    self.__repeatState__ = "none"
                else:
                    self.__repeatState__ = "playlist"
                ## Update repeat button to appropriate unicode
                window["repeat_toggle"].update(self.__unicode_symbols__[f"repeat_{self.__repeatState__.lower()}"])
                window["repeat_toggle"].set_tooltip(f"Repeat: {self.__repeatState__.capitalize()}")
                self.__updateRepeatState__()
            elif self.__event__ == "shuffle_toggle":
                self.__shuffleState__ = not self.__shuffleState__
                ## Update shuffle tooltip indicator
                window["shuffle_toggle"].set_tooltip(f"Shuffle: {str(self.__shuffleState__).replace('True', 'On').replace('False', 'Off')}")
                self.__sendCommand__(self.__event__)
            elif self.__event__ == "play_pause":
                ## Events parsed by __sendCommand__ function
                self.__sendCommand__(self.__event__)
                ## Only the play/pause state is retrieved to verify command succeeded
                self.__fetchMetadata__(include_play_state=True, only_includes=True)
                ## Invert play/pause button color scheme
                # TODO: Fix broken highlight color
                if self.__playState__.lower().strip() == "paused":
                    # window["play_pause"].Widget.config(highlightcolor="black")
                    window["play_pause"].update(button_color=("black", "white"))
                else:
                    # window["play_pause"].Widget.config(highlightcolor="white")
                    window["play_pause"].update(button_color=("white", "black"))
            elif self.__event__:
                self.__updateRemoteHost__(self.__values__.get("remoteIPaddress", self.__remoteHost__))
                self.__sendCommand__(self.__event__)
                self.__fetchMetadata__()
                window["current_title"].update(self.__metadata__.get("title", "Unknown Track"))
                window["current_artist"].update(self.__metadata__.get("artist", "Unknown Track"))
                window["current_album"].update(self.__metadata__.get("album", "Unknown Track"))
                window["current_image"].update(self.__metadata__.get("image", "Unknown Track"))
        window.close()

    def __updateRepeatState__(self):
        # TODO: Add repeat controls for CMUS
        if self.__mode__ == "cmus":
            pass
        elif self.__mode__ in ["ssh", "playerctl"]:
            subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl loop {self.__repeatState__}", stdout=subprocess.PIPE, shell=True).communicate()

    def __updateRemoteHost__(self, host):
        if not host:
            return

        if self.ipv4_pattern.match(host):
            self.__remoteHost__ = host

        # TODO: Add IPv6 support

    def __updatePlaybackVolume__(self, volume):
        if not self.__remoteHost__:
            return
        elif int(str(volume).replace("%", "")) not in range(0,101):
            print("Invalid volume!")
            return

        self.__playbackVolume__ = volume

        if self.__mode__ == "cmus":
            subprocess.Popen(f"cmus-remote --server {self.__remoteHost__}:{self.__remoteHostPort__} --passwd {self.__remoteHostPassword__} -v {volume}%", stdout=subprocess.PIPE, shell=True).communicate()
        ## SSH or playerctl accepted as modes
        elif self.__mode__ in ["ssh", "playerctl"]:
            subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} pactl set-sink-volume @DEFAULT_SINK@ {volume}%", stdout=subprocess.PIPE, shell=True).communicate()

    def __sendCommand__(self, command):
        if not self.__remoteHost__:
            return

        ## Commands initialized for SSH/playerctl, replaced when using CMUS
        if command == "play_pause":
            if self.__mode__ == "cmus":
                command = "-u"
            elif self.__mode__ in ["ssh", "playerctl"]:
                command = command.replace("_", "-")
        elif command == "previous":
            if self.__mode__ == "cmus":
                command = "-r"
        elif command == "next":
            if self.__mode__ == "cmus":
                command = "-n"
        elif command == "seek_back":
            command = f"position {self.__seekDuration__}"
            if self.__mode__ == "cmus":
                command = command.replace("position ", "-k -")
            else:
                command += "-"
        elif command == "seek_forward":
            command = f"position {self.__seekDuration__}"
            if self.__mode__ == "cmus":
                command = command.replace("position ", "-k +")
            else:
                command += "+"
        ## Additional commands go here
        elif command == "shuffle_toggle":
            if self.__mode__ == "cmus":
                command = "-S"
            else:
                command = command.replace("_", " ")

        if self.__mode__ == "cmus":
            subprocess.Popen(f"cmus-remote --server {self.__remoteHost__}:{self.__remoteHostPort__} --passwd {self.__remoteHostPassword__} {command}", stdout=subprocess.PIPE, shell=True).communicate()
        elif self.__mode__ in ["ssh", "playerctl"]:
            subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl {command}", stdout=subprocess.PIPE, shell=True).communicate()

    def __fetchMetadata__(self, **kwargs):
        ## Load fetch options
        include_volume = kwargs.get("include_volume", False)
        include_play_state = kwargs.get("include_play_state", False)
        include_playback_controls = kwargs.get("include_playback_controls", False)
        only_includes = kwargs.get("only_includes", False)

        ## Create default metadata set
        self.__metadata__ = {"title": "Unknown Track", "artist": "Unknown Artist", "album": "Unknown Album", "image": "default.png"}

        if self.__mode__ in ["ssh", "playerctl"]:
            ## Run include conditions first, to allow for clean exit
            ## with only_includes
            if include_volume:
                new_volume = subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} pactl get-sink-volume @DEFAULT_SINK@", stdout=subprocess.PIPE, shell=True).communicate()[0].decode().split("%")[0].split(" ")[-1]
                if new_volume:
                    self.__playbackVolume__ = new_volume
            if include_play_state:
                self.__playState__ = subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl status", stdout=subprocess.PIPE, shell=True).communicate()[0].decode().lower()
            if include_playback_controls:
                self.__repeatState__, self.__shuffleState__ = subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl loop; playerctl shuffle", stdout=subprocess.PIPE, shell=True).communicate()[0].decode().split("\n")[:-1]
                self.__shuffleState__ = True if self.__shuffleState__ == "On" else False
            ## Do not make SSH requests if not required
            if not only_includes:
                metadata = subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl metadata", stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
                # Parse standard metadata set from playerctl
                for line in metadata.split("\n"):
                    if "xesam:artist" in line:
                        self.__metadata__["artist"] = line.split("xesam:artist")[1].strip()
                    elif "xesam:album" in line:
                        self.__metadata__["album"] = line.split("xesam:album")[1].strip()
                    elif "xesam:title" in line:
                        self.__metadata__["title"] = line.split("xesam:title")[1].strip()
                    elif "mpris:artUrl" in line:
                        # NOTE: Most artwork files are placed in ~/.cache
                        # NOTE: VLC, and some other media players use non-standard
                        # NOTE: filepaths, which cannot be understood by SCP. The
                        # NOTE: default.png is used in such cases
                        remoteImage = line.split("mpris:artUrl")[1].split("file://")[1].replace("%20", " ").strip()
                        ## Images placed in /tmp directory to avoid bloat
                        self.__metadata__["image"] = f"/tmp/user/1000/{hashlib.sha256(os.path.basename(remoteImage).encode()).hexdigest()}.png".strip()

                        ## Relying on stored artwork versions averts unneeded file transfers
                        if not os.path.exists(self.__metadata__["image"]):
                            subprocess.Popen(f"scp -P {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__}:{remoteImage} {self.__metadata__['image']}", stdout=subprocess.PIPE, shell=True).communicate()
                            ## If SCP fails, use default image
                            if not os.path.exists(self.__metadata__["image"]):
                                self.__metadata__["image"] = "default.png"

    def __generateCopyrightElement__(self):
        ## Create one-time copyright element
        layout=[gui.Text(f"remote-media-controller {self.__version__.strip()} (C) le-firehawk 2023", font="Courier 6")]
        return layout

def load_params(vals):
    ## Build dictionary of parameters
    parameters={}
    for i, val in enumerate(vals):
        ## Mode for command execution
        if val in ["--mode", "-m"]:
            parameters['mode'] = vals[i+1]
            del vals[i+1]
        ## IP address of host playing media
        elif val in ["--ip", "-h"]:
            parameters['remoteHost'] = vals[i+1]
            del vals[i+1]
        ## Port for CMUS or SSH connections
        elif val in ["--port", "-P"]:
            parameters['remotePort'] = vals[i+1]
            del vals[i+1]
        ## User for SSH connections
        elif val in ["--user", "-u"]:
            parameters['remoteUser'] = vals[i+1]
            del vals[i+1]
        ## Password for CMUS-remote server, not SSH
        elif val in ["--password", "-p"]:
            parameters['password'] = vals[i+1]
            del vals[i+1]
    if len(parameters) == 0:
        usage()
        exit()
    return parameters

def usage():
    print("Usage:")
    print(f"    {sys.argv[0]} [<option>...]")
    print("e.g.")
    print(f"    {sys.argv[0]} --mode ssh --ip 192.168.0.2 --port 22 --user user")
    print("Options:")
    print(f"    -m, --mode      [e.g. ssh]")
    print(f"    -h, --ip        [e.g. 192.168.0.2]")
    print(f"    -P, --port      [e.g. 22]")
    print(f"    -u, --user      [e.g. user]")
    print(f"    -p, --password  [e.g. password]")

def main(version):
    try:
        parameters = load_params(sys.argv)
        controllerInstance = controller(parameters, version)
    except IndexError:
        print("Missing required parameters!")
        usage()

if __name__ == "__main__":
    ## Load version information
    with open("./version.txt") as version_file:
        version = version_file.read()
    main(version)
