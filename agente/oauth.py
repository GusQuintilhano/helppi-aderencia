"""OAuth mínimo para clientes remotos que exigem login (o Gemini exige).

Não há usuário para autenticar: o acesso já é protegido pelo token secreto no
caminho da URL, e os dados do case são só de leitura. Por isso o /authorize
aprova na hora e devolve o código direto ao cliente. O resto segue o fluxo
OAuth 2.1 do SDK do MCP (registro dinâmico, PKCE, troca de código).

Clientes e códigos ficam em memória; um restart do container pede para
reconectar o app no Gemini. Os access tokens são assinados (HMAC com o
MCP_TOKEN), então os já emitidos continuam válidos depois de um restart.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

VALIDADE_ACCESS = 30 * 24 * 3600
VALIDADE_CODIGO = 300


class ProvedorAutoAprovado:
    def __init__(self, segredo: str) -> None:
        self.segredo = segredo.encode()
        self.clientes: dict[str, OAuthClientInformationFull] = {}
        self.codigos: dict[str, AuthorizationCode] = {}
        self.refresh: dict[str, RefreshToken] = {}

    # Access tokens assinados: payload.assinatura, ambos em base64url.
    def _assinar(self, dados: dict) -> str:
        payload = base64.urlsafe_b64encode(json.dumps(dados).encode()).rstrip(b"=")
        assinatura = hmac.new(self.segredo, payload, hashlib.sha256).digest()
        return f"{payload.decode()}.{base64.urlsafe_b64encode(assinatura).rstrip(b'=').decode()}"

    def _emitir(self, client_id: str, scopes: list[str], resource: str | None) -> OAuthToken:
        expira = int(time.time()) + VALIDADE_ACCESS
        access = self._assinar({"c": client_id, "s": scopes, "r": resource, "e": expira, "n": secrets.token_hex(4)})
        refresh = secrets.token_urlsafe(32)
        self.refresh[refresh] = RefreshToken(token=refresh, client_id=client_id, scopes=scopes, resource=resource)
        return OAuthToken(
            access_token=access, token_type="Bearer", expires_in=VALIDADE_ACCESS,
            refresh_token=refresh, scope=" ".join(scopes) or None,
        )

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self.clientes.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self.clientes[client_info.client_id] = client_info

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        codigo = secrets.token_urlsafe(32)
        self.codigos[codigo] = AuthorizationCode(
            code=codigo,
            scopes=params.scopes or [],
            expires_at=time.time() + VALIDADE_CODIGO,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
        )
        return construct_redirect_uri(str(params.redirect_uri), code=codigo, state=params.state)

    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str) -> AuthorizationCode | None:
        codigo = self.codigos.get(authorization_code)
        return codigo if codigo and codigo.client_id == client.client_id else None

    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode) -> OAuthToken:
        self.codigos.pop(authorization_code.code, None)
        return self._emitir(client.client_id, authorization_code.scopes, authorization_code.resource)

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        token = self.refresh.get(refresh_token)
        return token if token and token.client_id == client.client_id else None

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        self.refresh.pop(refresh_token.token, None)
        return self._emitir(client.client_id, scopes or refresh_token.scopes, refresh_token.resource)

    async def load_access_token(self, token: str) -> AccessToken | None:
        try:
            payload, assinatura = token.split(".")
            esperado = base64.urlsafe_b64encode(hmac.new(self.segredo, payload.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
            if not hmac.compare_digest(assinatura, esperado):
                return None
            dados = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        except ValueError:
            return None
        if dados["e"] < time.time():
            return None
        return AccessToken(token=token, client_id=dados["c"], scopes=dados["s"], expires_at=dados["e"], resource=dados["r"])

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        self.refresh.pop(token.token, None)
