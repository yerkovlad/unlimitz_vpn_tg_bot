import aiohttp
import uuid
import json
import logging
from config import PANEL_USERNAME, PANEL_PASSWORD

logger = logging.getLogger(__name__)


class VlessClient:
    def __init__(self, ip: str, port: int, inbound_id: int, uri_path: str = "/"):
        self.base_url = f"https://{ip}:{port}{uri_path.rstrip('/')}"
        self.inbound_id = inbound_id
        self.ip = ip
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        await self._login()
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def _login(self) -> bool:
        async with self._session.post(f"{self.base_url}/login", json={
            "username": PANEL_USERNAME,
            "password": PANEL_PASSWORD
        }) as r:
            text = await r.text()
            data = json.loads(text) if text else {}
            success = data.get("success", False)
            if not success:
                logger.error("Login failed for %s", self.base_url)
            return success

    async def ping(self) -> bool:
        try:
            async with self._session.get(
                f"{self.base_url}/panel/api/inbounds/get/{self.inbound_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as r:
                return r.status == 200
        except Exception:
            return False

    async def get_client_count(self) -> int:
        try:
            async with self._session.get(
                f"{self.base_url}/panel/api/inbounds/get/{self.inbound_id}"
            ) as r:
                data = await r.json(content_type=None)
                obj = data.get("obj", {})
                settings = json.loads(obj.get("settings", "{}"))
                return len(settings.get("clients", []))
        except Exception:
            return 0

    async def create_client(self, name: str, traffic_gb: int = 0, days: int = 30) -> tuple[str, bool]:
        client_id = str(uuid.uuid4())
        traffic_bytes = traffic_gb * 1024 ** 3 if traffic_gb > 0 else 0

        import time
        expiry_time = int((time.time() + days * 86400) * 1000)

        client = {
            "id": client_id,
            "email": name,
            "limitIp": 1,
            "totalGB": traffic_bytes,
            "expiryTime": expiry_time,
            "enable": True,
            "tgId": "",
            "subId": ""
        }

        async with self._session.post(
            f"{self.base_url}/panel/api/inbounds/addClient",
            json={"id": self.inbound_id, "settings": json.dumps({"clients": [client]})}
        ) as r:
            text = await r.text()
            result = json.loads(text) if text else {}
            success = result.get("success", False)
            if not success:
                logger.error("create_client failed: %s", text)
            return client_id, success

    async def get_link(self, client_id: str, name: str) -> str | None:
        try:
            async with self._session.get(
                f"{self.base_url}/panel/api/inbounds/get/{self.inbound_id}"
            ) as r:
                data = await r.json(content_type=None)
                obj = data["obj"]

            stream = json.loads(obj["streamSettings"])
            reality = stream["realitySettings"]

            pbk = reality["settings"]["publicKey"]
            sni = reality["serverNames"][0]
            sid = reality["shortIds"][0]

            return (
                f"vless://{client_id}@{self.ip}:{obj['port']}"
                f"?type=tcp&encryption=none&security=reality"
                f"&pbk={pbk}&fp=chrome&sni={sni}&sid={sid}&spx=%2F#{name}"
            )
        except Exception as e:
            logger.error("get_link error: %s", e)
            return None

    async def delete_client(self, client_id: str) -> bool:
        async with self._session.post(
            f"{self.base_url}/panel/api/inbounds/{self.inbound_id}/delClient/{client_id}"
        ) as r:
            text = await r.text()
            result = json.loads(text) if text else {}
            return result.get("success", False)


async def generate_vless_link(server, name: str, days: int = 30, traffic_gb: int = 100) -> tuple[str, str] | None:
    try:
        async with VlessClient(server.ip, server.port, server.inbound_id, server.uri_path) as client:
            client_id, success = await client.create_client(name, traffic_gb=traffic_gb, days=days)
            if not success:
                logger.error("create_client failed for server %s", server.ip)
                return None
            link = await client.get_link(client_id, name)
            logger.info("Generated link: %s", link)
            return link, client_id  # возвращаем оба
    except Exception as e:
        logger.error("generate_vless_link error: %s", e)
        return None


async def check_server_alive(server) -> bool:
    try:
        async with VlessClient(server.ip, server.port, server.inbound_id, server.uri_path) as client:
            return await client.ping()
    except Exception:
        return False

async def delete_vless_client(server, profile_id: str) -> bool:
    try:
        async with VlessClient(server.ip, server.port, server.inbound_id, server.uri_path) as client:
            return await client.delete_client(profile_id)
    except Exception as e:
        logger.error("delete_vless_client error: %s", e)
        return False