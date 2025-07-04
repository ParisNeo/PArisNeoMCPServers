from mcp.server.auth.provider import AccessToken, TokenVerifier
import httpx
import os
from contextvars import ContextVar

AUTHORIZATION_SERVER_URL = os.environ.get("AUTHORIZATION_SERVER_URL","http://localhost:9642")

class MyTokenInfo(AccessToken):
    user_id: int | None = None
    username: str | None = None
    
token_info_context: ContextVar[MyTokenInfo | None] = ContextVar("token_info_context", default=None)

# This is our set of valid API keys. In a real app, you'd check a database.
class IntrospectionTokenVerifier(TokenVerifier):
    """
    Ce verifier demande au serveur d'autorisation si un token est valide.
    Il est complètement agnostique à la manière dont les tokens sont créés.
    """
    async def verify_token(self, token: str) -> AccessToken:
        # Fait un appel HTTP sécurisé à votre endpoint /introspect
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{AUTHORIZATION_SERVER_URL}/api/auth/introspect",
                    data={"token": token}
                )
                response.raise_for_status() # Lève une exception pour les erreurs 4xx/5xx
            except httpx.RequestError as e:
                print(f"ERROR: Could not connect to introspection endpoint: {e}")
                return AccessToken(active=False)

        # Crée un objet TokenInfo directement à partir de la réponse JSON
        token_info_dict = response.json()
        token_info_dict["token"] = token
        token_info_dict["client_id"] = str(token_info_dict.get("user_id"))
        token_info_dict["scopes"] = []
        token_info = MyTokenInfo(**token_info_dict)

        # --- L'ÉTAPE CRUCIALE ---
        # Définissez la valeur de la variable de contexte pour cette requête.
        token_info_context.set(token_info)
        return MyTokenInfo(**token_info_dict)
    
# to recover the user information, just use token_info = token_info_context.get()
