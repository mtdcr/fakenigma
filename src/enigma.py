# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2022 Andreas Oberritter
# SPDX-License-Identifier: MIT
#

import ctypes
import subprocess
from xml.etree import ElementTree

import requests
from six.moves.urllib.parse import unquote, urljoin


class _WebInterface:
    base_url = "http://localhost/web/"

    def __init__(self):
        self._session_id = None
        self._session_id = self.session_id()

    def get(self, endpoint, params={}):
        if self._session_id:
            params["sessionid"] = self._session_id
        url = urljoin(self.base_url, endpoint)
        r = requests.get(url, params=params, timeout=3, verify=False)
        assert r.status_code == 200
        return ElementTree.fromstring(r.text)

    def post(self, endpoint, data):
        if self._session_id:
            data["sessionid"] = self._session_id
        url = urljoin(self.base_url, endpoint)
        r = requests.post(url, data=data, timeout=3, verify=False)
        assert r.status_code == 200
        return ElementTree.fromstring(r.text)

    def session_id(self):
        root = self.get("session")
        assert root.tag == "e2sessionid"
        return root.text


class eDVBDB:
    @classmethod
    def getInstance(cls):
        return cls

    @classmethod
    def reloadBouquets(cls):
        _WebInterface().post("servicelistreload", {"mode": 2})


class eServiceReference:
    idDVB = 1
    idM2TS = 3
    idUser = 4096
    idGST = 4097
    idURI = 8193
    idStream = 8739

    flagDirectory = 7
    isMarker = 64
    isGroup = 128
    isLive = 256

    def __init__(self, *args):
        if len(args) == 0:
            self._type = 0
            self._flags = 0
            self._data = [0] * 8
            self._path = ""
            self._name = ""

        elif len(args) == 1 and isinstance(args[0], bytes):
            parts = args[0].split(":")
            assert len(parts) >= 11
            self._type = int(parts[0])
            self._flags = int(parts[1])
            self._data = [int(n, 16) for n in parts[2:10]]
            self._path = unquote(parts[10])
            if len(parts) >= 12:
                self._name = unquote(parts[11])
            else:
                self._name = ""

        elif (
            len(args) == 3
            and isinstance(args[0], int)
            and isinstance(args[1], int)
            and isinstance(args[2], bytes)
        ):
            self._type = args[0]
            self._flags = args[1]
            self._data = [0] * 8
            self._path = args[2]
            self._name = ""

        else:
            raise ValueError("Unimplemented constructor")

    def getData(self, idx):
        assert isinstance(idx, int)
        if idx < len(self._data):
            return ctypes.c_int32(self._data[idx]).value
        return 0

    def getUnsignedData(self, idx):
        assert isinstance(idx, int)
        if idx < len(self._data):
            return ctypes.c_uint32(self._data[idx]).value
        return 0

    def setData(self, idx, value):
        assert isinstance(idx, int)
        assert isinstance(value, int)
        if idx < len(self._data):
            self._data[idx] = value

    def setName(self, name):
        assert isinstance(name, bytes)
        self._name = name

    def setPath(self, path):
        assert isinstance(path, bytes)
        self._path = path

    def toString(self):
        parts = [str(self._type), str(self._flags)]
        parts += ["{:x}".format(self.getUnsignedData(n)) for n in range(len(self._data))]
        parts.append(self._encode(self._path))
        if self._name:
            parts.append(self._encode(self._name))
        return ":".join(parts)

    def _encode(self, s):
        assert isinstance(s, bytes)
        parts = []
        for c in s.decode("utf-8"):
            if c in (":", "%") or ord(c) < 32:
                parts.append("%{:02x}".format(ord(c)))
            else:
                parts.append(c)

        return "".join(parts)


def getEnigmaVersionString():
    root = _WebInterface().get("deviceinfo")
    assert root.tag == "e2deviceinfo"
    return root.find("e2enigmaversion").text
