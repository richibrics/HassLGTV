import http.client
import xml.etree.ElementTree as etree
import socket
import logging
import requests
import time
import urllib
import os
import re
import sys
import voluptuous as vol

from homeassistant.components.media_player import (
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK, PLATFORM_SCHEMA,
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_SET, SUPPORT_PLAY, MEDIA_PLAYER_SCHEMA,
    SUPPORT_VOLUME_MUTE, MEDIA_TYPE_VIDEO, MEDIA_TYPE_TVSHOW, MediaPlayerDevice)

from homeassistant.const import (
    CONF_API_KEY, STATE_OFF, STATE_IDLE, STATE_PAUSED, STATE_PLAYING)
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.discovery import async_load_platform
# from var_dump import var_dump
import homeassistant.helpers.config_validation as cv

lgtv = {}
dialogMsg = ""
headers = {"Content-Type": "application/atom+xml"}
lgtv["pairingKey"] = ""
found = False

SUPPORT_LGSMARTTV = SUPPORT_VOLUME_SET | SUPPORT_PAUSE |\
    SUPPORT_PLAY | SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK |\
    SUPPORT_VOLUME_MUTE | SUPPORT_TURN_OFF

DEFAULT_NAME = 'LgSmartTV2013'
DOMAIN = 'media_player'
PLATFORM_NAME = 'lgsmarttv2013'

CONF_CLIENT_SECRET = 'client_secret'
CONF_CLIENT_ADDRESS = 'client_address'
CONF_CLIENT_ID = 'client_personal_id'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_CLIENT_ADDRESS, default="none"): cv.string,
    vol.Optional(CONF_CLIENT_ID, default="x"): cv.string,
    vol.Optional(CONF_CLIENT_SECRET, default=0): cv.positive_int
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Save config in global variable"""
    global configIpAddress
    global configClientID
    """IP assign is inside getip function"""
    configClientID = config.get(CONF_CLIENT_ID)
    configIpAddress = config.get(CONF_CLIENT_ADDRESS)
    lgtv["pairingKey"] = config.get(CONF_CLIENT_SECRET)
    add_entities([LGSmartTv2013()], True)
    return True


class LGSmartTv2013(MediaPlayerDevice):
    def __init__(self):
        self._name = "LG_Smart_TV_2013_"+configClientID
        self._state = STATE_OFF
        self._volumeLevel = 0
        self._isMuted = False
        self._currentChannelNumber = 0
        self._currentChannelName = "Channel"
        self._currentProgram = "Program"
        self._currentSourceName = "Antenna"
        self._currentSourceNumber = "0"
        self._changeImageIndex = 0
        """Used to change image when program changes (with at symbol)"""
        self.connect()

    @property
    def name(self):
        """Return the device name."""
        return self._name

    @property
    def should_poll(self):
        """Device should be polled."""
        return True

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_LGSMARTTV

    @property
    def state(self):
        """Return the state of the player."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volumeLevel/100

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._isMuted

    @property
    def media_title(self):
        """Title of current playing media."""
        if lgtv["pairingKey"] == 0:
            return "Pin not set"
        if self._currentSourceNumber == "0":
            return self._currentProgram
        else:
            return self._currentSourceName

    @property
    def media_series_title(self):
        """Artist of current playing media, music track only."""
        if lgtv["pairingKey"] == 0:
            return "Pin not set"
        if self._currentSourceNumber == "0":
            return ("{0} - CH{1:d} - {2}").format(self._currentSourceName, self._currentChannelNumber, self._currentChannelName)
        else:
            return ""

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        return self._imageUrl

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_TVSHOW

    @property
    def media_duration(self):
        """In secondi"""
        return None

    def update(self):
        """Get the latest date and update device state."""
        self.getPower()
        if self._state != STATE_OFF:
            self.getVolume()
            self.getCurrentChannel()

    def turn_off(self):
        """Turn off the device."""
        self.handleCommand(1)
        self._state = STATE_OFF

    def media_play(self):
        """Send play command."""
        self.handleCommand(33)
        self._state = STATE_PLAYING

    def media_pause(self):
        """Send pause command."""
        self.handleCommand(34)
        self._state = STATE_PAUSED

    def volume_up(self):
        """Send volume up command."""
        self.handleCommand(24)

    def volume_down(self):
        """Send volume down command."""
        self.handleCommand(25)

    def media_previous_track(self):
        """Send previous track command (results in rewind)."""
        self.handleCommand(28)

    def media_next_track(self):
        """Send next track command (results in fast-forward)."""
        self.handleCommand(27)

    def mute_volume(self, mute):
        """Mute the volume."""
        self.handleCommand(26)

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        targetVolume = volume * 100
        tempVolume = -1
        oldVolume = -2
        i = 0
        while int(targetVolume) != tempVolume:
            self.getVolume()
            tempVolume = self._volumeLevel
            i = i + 1
            if tempVolume != oldVolume or i >= 10:
                i = 0
                if tempVolume > targetVolume:
                    self.volume_down()
                else:
                    self.volume_up()
                oldVolume = tempVolume

    """ Codice Per Televisione """

    def handleData(self, cmdcode):
        conn = http.client.HTTPConnection(lgtv["ipaddress"], port=8080)
        conn.request("GET", "/roap/api/data?target=" +
                     cmdcode, headers=headers)
        httpResponse = conn.getresponse()
        return httpResponse

    def getVolume(self):
        httpResponse = None
        try:
            httpResponse = self.handleData('volume_info')
            tree = etree.parse(httpResponse)
            root = tree.getroot()
            child = root[2][3]
            self._volumeLevel = int(child.text)
            child = root[2][0]
            if child.text == "false":
                self._isMuted = False
            else:
                self._isMuted = True
        except:
            print("Can't get volume information: " + str(httpResponse.reason))
            if httpResponse.reason == "Unauthorized":
                self.getSessionid()

    def getCurrentChannel(self):
        httpResponse = None
        try:
            httpResponse = self.handleData('cur_channel')
            tree = etree.parse(httpResponse)
            root = tree.getroot()
            child = root[2][3]
            self._currentChannelNumber = int(child.text)
            child = root[2][7]
            self._currentChannelName = child.text
            child = root[2][8]
            if self._currentProgram != child.text:
                self._changeImageIndex = self._changeImageIndex + 1
                self._imageUrl = "http://" + \
                    str(self._changeImageIndex) + "@" + \
                    lgtv["ipaddress"] + \
                    ":8080//roap/api/data?target=screen_image"
            self._currentProgram = child.text
            child = root[2][10]
            self._currentSourceName = child.text
            child = root[2][11]
            if self._currentSourceNumber != child.text:
                self._changeImageIndex = self._changeImageIndex + 1
                self._imageUrl = "http://" + \
                    str(self._changeImageIndex) + "@" + \
                    lgtv["ipaddress"] + \
                    ":8080//roap/api/data?target=screen_image"
            self._currentSourceNumber = child.text
        except:
            print("Can't get channel information: " + str(httpResponse.reason))
            if httpResponse.reason == "Unauthorized":
                self.getSessionid()

    def getPower(self):
        if lgtv["ipaddress"] != None:
            if not self.isOnline():
                self.getip()
                if lgtv["ipaddress"] == None:
                    self._state = STATE_OFF
            else:
                if self._state == STATE_OFF:
                    self._state = STATE_PLAYING
                """If before TV was ON I don't set it ON cause it can be playing or paused and I have already set that state"""
        else:
            self.getip()
            if lgtv["ipaddress"] != None:
                self.update()

    def isOnline(self):
        """Make a ping on this device's ip: return 1 if online, 0 if offline"""
        response = os.system("ping -c 1 " + lgtv["ipaddress"])
        if(response != 0):
            return 0
        return 1

    def connect(self):
        self.getip()
        if self._state != STATE_OFF:
            theSessionid = self.getSessionid()
            while theSessionid == "Unauthorized":
                self.displayKey()
                theSessionid = self.getSessionid()
            if len(theSessionid) < 8:
                sys.exit("Could not get Session Id: " + theSessionid)
            self._imageUrl = "http://" + \
                str(self._changeImageIndex) + "@" + \
                lgtv["ipaddress"] + ":8080//roap/api/data?target=screen_image"
            lgtv["session"] = theSessionid

    def getip(self):
        """If there's no ip in config file I search otherwise I return the configuration IP"""
        if configIpAddress == "none":
            strngtoXmit = 'M-SEARCH * HTTP/1.1' + '\r\n' + \
                'HOST: 239.255.255.250:1900' + '\r\n' + \
                'MAN: "ssdp:discover"' + '\r\n' + \
                'MX: 2' + '\r\n' + \
                'ST: urn:schemas-upnp-org:device:MediaRenderer:1' + '\r\n' + '\r\n'

            bytestoXmit = strngtoXmit.encode()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            gotstr = 'notyet'
            found = False
            ipaddress = None
            sock.sendto(bytestoXmit,  ('239.255.255.250', 1900))
            try:
                gotbytes, addressport = sock.recvfrom(512)
                gotstr = gotbytes.decode()
            except:
                sock.sendto(bytestoXmit, ('239.255.255.250', 1900))
            if re.search('LG', gotstr):
                ipaddress, _ = addressport
                found = True
                self._state = STATE_PLAYING
            else:
                gotstr = 'notyet'
            sock.close()
            if not found:
                print("LG TV not found")
                ipaddress = None
                self._state = STATE_OFF
            lgtv["ipaddress"] = ipaddress
        else:
            lgtv["ipaddress"] = configIpAddress
            if self.isOnline():
                self._state = STATE_PLAYING
            else:
                self._state = STATE_OFF

    def displayKey(self):
        conn = http.client.HTTPConnection(lgtv["ipaddress"], port=8080)
        reqKey = "<?xml version=\"1.0\" encoding=\"utf-8\"?><auth><type>AuthKeyReq</type></auth>"
        conn.request("POST", "/roap/api/auth", reqKey, headers=headers)
        httpResponse = conn.getresponse()
        time.sleep(1000)
        if httpResponse.reason != "OK":
            sys.exit("Network error")
        return httpResponse.reason

    def getSessionid(self):
        conn = http.client.HTTPConnection(lgtv["ipaddress"], port=8080)
        pairCmd = "<?xml version=\"1.0\" encoding=\"utf-8\"?><auth><type>AuthReq</type><value>{0}</value></auth>".format(
            lgtv["pairingKey"])
        conn.request('POST', '/roap/api/auth', pairCmd, headers=headers)
        httpResponse = conn.getresponse()
        if httpResponse.reason != "OK":
            return httpResponse.reason
        tree = etree.XML(httpResponse.read())
        return tree.find('session').text

    def handleCommand(self, cmdcode):
        conn = http.client.HTTPConnection(lgtv["ipaddress"], port=8080)
        cmdText = "<?xml version=\"1.0\" encoding=\"utf-8\"?><command>" \
            + "<name>HandleKeyInput</name><value>" \
            + str(cmdcode) \
            + "</value></command>"
        conn.request("POST", "/roap/api/command", cmdText, headers=headers)
        httpResponse = conn.getresponse()
        return httpResponse.reason
