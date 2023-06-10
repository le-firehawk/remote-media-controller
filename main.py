#!/usr/bin/python3

import PySimpleGUI as gui
import subprocess, re, sys, os, hashlib

gui.theme("black")

class controller:
    def __init__(self, parameters):
        self.ipv4_pattern, self.ipv6_pattern = re.compile("[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"), None
        self.__event__, self.__values__ = True, ""
        self.__remoteHost__, self.__remoteHostPort__, self.__remoteHostUser__, self.__remoteHostPassword__, self.__mode__ = parameters.get("remoteHost",None), parameters.get("remotePort", 662), parameters.get("remoteUser", None), parameters.get("password", None), parameters.get("mode", "cmus")
        self.__seekDuration__, self.__playbackVolume__ = "5S", 100
        self.__repeatState__, self.__playState__ = "playlist", "paused"
        self.__fetchMetadata__(include_volume=True, include_play_state=True)
        self.__openWindow__()

    def __openWindow__(self):
        self.__layout__ = [[gui.Text("IP Address: "), gui.InputText(key="remoteIPaddress", default_text=self.__remoteHost__, size=(10,5)), gui.Button("🔄", key="refresh_metadata")], [gui.Text(self.__metadata__.get("title", "Unknown Track"), key="current_title", size=(25,2))], [gui.Text(self.__metadata__.get("artist", "Unknown Artist"), key="current_artist", size=(25,2))], [gui.Text(self.__metadata__.get("album", "Unknown Album"), key="current_album", size=(25,2))], [gui.Button("🔀", key="toggle_shuffle"), gui.Button("🔁", key="repeat_toggle"), gui.Button("⏮︎", key="previous"), gui.Button("⏪︎", key="seek_back"), gui.Button("⏯︎", key="play_pause", bind_return_key=True, button_color=("white", "black") if self.__playState__.lower().strip() == "playing" else ("black", "white")), gui.Button("⏩︎", key="seek_forward"), gui.Button("⏭︎", key="next")], [gui.Image(self.__metadata__.get("image", "default.png"), size=(384,384), key="current_image"), gui.Slider(range=(0,100), key="volume_control", orientation="v", default_value=self.__playbackVolume__)]]
        window = gui.Window(title="Firehawk's Media Controller", layout=self.__layout__, margins=(100, 50), font="Courier 30", finalize=True)
        window["volume_control"].bind('<ButtonRelease-1>', "-update")
        while self.__event__:
            self.__event__, self.__values__ = window.read()
            if self.__event__ == "volume_control-update":
                self.__updatePlaybackVolume__(int(self.__values__.get("volume_control", self.__playbackVolume__)))
            elif self.__event__ == "refresh_metadata":
                self.__fetchMetadata__(include_volume=True, include_play_state=True)
                window["current_title"].update(self.__metadata__.get("title", "Unknown Track"))
                window["current_artist"].update(self.__metadata__.get("artist", "Unknown Track"))
                window["current_album"].update(self.__metadata__.get("album", "Unknown Track"))
                window["current_image"].update(self.__metadata__.get("image", "Unknown Track"))
                window["volume_control"].update(self.__playbackVolume__)
            elif self.__event__ == "repeat_toggle":
                if self.__repeatState__ == "playlist":
                    self.__repeatState__ = "track"
                    window["repeat_toggle"].update("🔂")
                elif self.__repeatState__ == "track":
                    self.__repeatState__ = "none"
                    window["repeat_toggle"].update("🠂")
                else:
                    self.__repeatState__ = "playlist"
                    window["repeat_toggle"].update("🔁")
                self.__updateRepeatState__()
            elif self.__event__ == "play_pause":
                self.__sendCommand__(self.__event__)
                self.__fetchMetadata__(include_play_state=True, only_includes=True)
                if self.__playState__.lower().strip() == "paused":
                    window["play_pause"].Widget.config(highlightcolor="black")
                    window["play_pause"].update(button_color=("black", "white"))
                else:
                    window["play_pause"].Widget.config(highlightcolor="white")
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
        if self.__mode__ == "cmus":
            pass
        elif self.__mode__ in ["ssh", "playerctl"]:
            subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl loop {self.__repeatState__}", stdout=subprocess.PIPE, shell=True).communicate()

    def __updateRemoteHost__(self, host):
        if not host:
            return

        if self.ipv4_pattern.match(host):
            self.__remoteHost__ = host

    def __updatePlaybackVolume__(self, volume):
        if not self.__remoteHost__:
            return
        elif int(str(volume).replace("%", "")) not in range(0,101):
            print("Invalid volume!")
            return

        self.__playbackVolume__ = volume

        if self.__mode__ == "cmus":
            subprocess.Popen(f"cmus-remote --server {self.__remoteHost__}:{self.__remoteHostPort__} --passwd {self.__remoteHostPassword__} -v {volume}%", stdout=subprocess.PIPE, shell=True).communicate()
        elif self.__mode__ in ["ssh", "playerctl"]:
            subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} pactl set-sink-volume @DEFAULT_SINK@ {volume}%", stdout=subprocess.PIPE, shell=True).communicate()

    def __sendCommand__(self, command):
        if not self.__remoteHost__:
            return

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
        if self.__mode__ == "cmus":
            subprocess.Popen(f"cmus-remote --server {self.__remoteHost__}:{self.__remoteHostPort__} --passwd {self.__remoteHostPassword__} {command}", stdout=subprocess.PIPE, shell=True).communicate()
        elif self.__mode__ in ["ssh", "playerctl"]:
            subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl {command}", stdout=subprocess.PIPE, shell=True).communicate()

    def __fetchMetadata__(self, **kwargs):
        include_volume, include_play_state, only_includes = kwargs.get("include_volume", False), kwargs.get("include_play_state", False), kwargs.get("only_includes", False)
        self.__metadata__ = {"title": "Unknown Track", "artist": "Unknown Artist", "album": "Unknown Album", "image": "default.png"}
        if self.__mode__ in ["ssh", "playerctl"]:
            if include_volume:
                new_volume = subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} pactl get-sink-volume @DEFAULT_SINK@", stdout=subprocess.PIPE, shell=True).communicate()[0].decode().split("%")[0].split(" ")[-1]
                if new_volume:
                    self.__playbackVolume__ = new_volume
            if include_play_state:
                self.__playState__ = subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl status", stdout=subprocess.PIPE, shell=True).communicate()[0].decode().lower()

            if not only_includes:
                metadata = subprocess.Popen(f"ssh -p {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__} playerctl metadata", stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
                for line in metadata.split("\n"):
                    if "xesam:artist" in line:
                        self.__metadata__["artist"] = line.split("xesam:artist")[1].strip()
                    elif "xesam:album" in line:
                        self.__metadata__["album"] = line.split("xesam:album")[1].strip()
                    elif "xesam:title" in line:
                        self.__metadata__["title"] = line.split("xesam:title")[1].strip()
                    elif "mpris:artUrl" in line:
                        remoteImage = line.split("mpris:artUrl")[1].split("file://")[1].replace("%20", " ").strip()
                        self.__metadata__["image"] = f"/tmp/user/1000/{hashlib.sha256(os.path.basename(remoteImage).encode()).hexdigest()}.png".strip()
                        if not os.path.exists(self.__metadata__["image"]):
                            subprocess.Popen(f"scp -P {self.__remoteHostPort__} {self.__remoteHostUser__}@{self.__remoteHost__}:{remoteImage} {self.__metadata__['image']}", stdout=subprocess.PIPE, shell=True).communicate()
                            if not os.path.exists(self.__metadata__["image"]):
                                self.__metadata__["image"] = "default.png"

def load_params(vals):
    parameters={}
    for i, val in enumerate(vals):
        if val in ["--mode", "-m"]:
            parameters['mode'] = vals[i+1]
            del vals[i+1]
        elif val in ["--ip", "-h"]:
            parameters['remoteHost'] = vals[i+1]
            del vals[i+1]
        elif val in ["--port", "-P"]:
            parameters['remotePort'] = vals[i+1]
            del vals[i+1]
        elif val in ["--user", "-u"]:
            parameters['remoteUser'] = vals[i+1]
            del vals[i+1]
        elif val in ["--password", "-p"]:
            parameters['password'] = vals[i+1]
            del vals[i+1]
    return parameters

try:
    parameters = load_params(sys.argv)
    controllerInstance = controller(parameters)
except IndexError:
    print("Missing required parameters!")
