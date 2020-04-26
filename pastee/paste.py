import aiohttp
import datetime
import json
from cryptography.fernet import Fernet
import typing
from contextlib import asynccontextmanager
if typing.TYPE_CHECKING:
    from typing import Dict, Optional, List, Union


class MainPaste:

    def __init__(self, data: dict):
        self.raw = data
        self._sucess = data["sucess"]
        self._id = data["paste"]["id"]
        self._encrypted = data["paste"]["encrypted"]
        self._description = data["paste"]["description"]
        self._views = data["paste"]["views"]
        self._created_at = datetime.datetime.fromisoformat(
            data["paste"]["created_at"]
        )
        self._expires_at = datetime.datetime.fromisoformat(
            data["paste"]["expires_at"]
        )
        self._sections = [PasteSection(d) for d in data["paste"]["sections"]]
        self.key

    @property
    def sucess(self):
        return self._sucess

    @property
    def id(self):
        return self._id

    @property
    def encrypted(self):
        return self._encrypted

    @property
    def description(self):
        return self._description

    @property
    def views(self):
        return self._views


class Syntax:

    def __init__(self, context):
        self.raw = context
        self._id = context["id"]
        self._short = context["short"]
        self._name = context["name"]

    @property
    def name(self):
        return self._name

    @property
    def short(self):
        return self._short

    @property
    def id(self):
        return self._id


class PasteSection:

    def __init__(self, context: dict):
        self.raw = context
        self._name = context["name"]
        self._syntax = Syntax(context["syntax"])
        self._contents = context["content"]

    @property
    def name(self):
        return self._name

    @property
    def syntax(self):
        return self._syntax

    @property
    def contents(self):
        return self._contents


class PasteFormat:

    def __init__(self, contents: str,
                 name: Optional[str] = "Paste",
                 syntax: Optional[str] = None):
        self._name = name
        self._syntax = syntax
        self._contents = contents

    @property
    def name(self):
        return self._name

    @property
    def syntax(self):
        return self._syntax

    @property
    def contents(self):
        return self._contents

    def __iter__(self):
        return self

    def __next__(self):
        return self


class Paste:

    def __init__(self, context: dict):
        self.raw = context
        self._id = context["id"]
        self._description = context["description"]
        self._created_at = datetime.datetime.fromisoformat(
            context["created_at"]
        )
        self._sections = [PasteSection(item) for item in context["sections"]]


class PasteResults:

    def __init__(self, paste: dict):
        self.raw = paste
        self._per_page = paste["per_page"]
        self._total = paste["total"]
        self._current_page = paste["current_page"]
        self._last_page = paste["last_page"]
        self._next_page_url = paste["next_page_url"]
        self._from = paste["from"]
        self._to = paste["to"]
        self._data = [Paste(item) for item in paste["data"]]

    @property
    def per_page(self):
        return self._per_page

    @property
    def total(self):
        return self._total

    @property
    def current_page(self):
        return self._current_page

    @property
    def last_page(self):
        return self._last_page

    @property
    def next_page_url(self):
        return self._next_page_url

    @property
    def start(self):
        return self._from

    @property
    def to(self):
        return self._to

    @property
    def data(self):
        self._data


class Client:
    def __init__(
            self, authorization: str, key: Optional[bytes] = None, **kwargs
            ) -> None:
        self.auth_code: str = authorization
        self.headers: Dict[str, str] = {}
        self.session: Union[aiohttp.ClientSession, None] = None
        self.API_BASE = kwargs.get("API_BASE", "https://api.paste.ee/v1")
        self.key = key
        self.fernet, = [Fernet(self.key) if self.key is not None else None]

    async def initialize(self) -> None:
        self.session = aiohttp.ClientSession()
        self.headers["X-Auth-Token"] = self.auth_code

    async def request(self, method: str,
                      url: str, **params) -> dict:
        async with self.session.request(method, f"{self.API_BASE}{url}",
                                        headers=self.headers,
                                        **params) as r:
            return await r.json(content_type=None)  # Server returns wrong mimetype # noqa

    async def post(self, url: str,
                   **params) -> dict:
        return await self.request("POST", url, **params)

    async def get(self, url: str,
                  **params) -> dict:
        return await self.request("GET", url, **params)

    async def delete(self, url: str,
                     **params) -> dict:
        return await self.request("DELETE", url, **params)

    async def get_pastes(self, page: int = 1, per_page: int = 25,
                         **params) -> PasteResults:
        return PasteResults(
            await self.get(f"/pastes?perpage={per_page}&page={page}", **params)
            )

    def encrypt(self, raw_text: bytes) -> bytes:
        if self.key is None:
            raise RuntimeError("Key not specified at client creation")
        return self.fernet.encrypt(raw_text)

    def decrypt(self, raw_text: bytes) -> bytes:
        if self.key is None:
            raise RuntimeError("Key not specified at client creation")
        return self.fernet.encrypt(raw_text)

    async def create_paste(self,
                           sections: Union[PasteFormat, List[PasteFormat]],
                           encrypted: Optional[bool] = False,
                           description: Optional[str] = "",
                           **params):
        paste_formats = []
        for section in sections:
            paste_formats.append({
                "name": section.name,
                "syntax": section.syntax,
                "contents": section.contents
            })
        body = json.dumps({
            "encrypt": encrypted,
            "description": description,
            "sections": paste_formats
        })
        return await self.post(
            "/pastes", headers={"Content-Type": "application/json"},
            data=body, **params)

    async def get_paste(self, paste_id: str) -> MainPaste:
        return MainPaste(await self.get(f"/pastes/{paste_id}"))

    async def delete_paste(self, paste_id: str) -> bool:
        r = await self.delete(f"/pastes/{paste_id}")
        return r["sucess"]

    @asynccontextmanager
    async def connection(*args, **kwargs):
        client = Client(*args, **kwargs)
        try:
            yield client
        finally:
            client.session.close()
