import aiohttp

class AsyncIKApi:
    def __init__(self, api_token: str):
        self.base_url = "https://api.indiankanoon.org"
        self.headers = {
            "Authorization": f"Token {api_token}",
            "Accept": "application/json"
        }

    async def fetch(self, endpoint: str, params=None):
        url = f"{self.base_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, data=params) as resp:
                return await resp.json()

    async def search(self, query: str, doctype: str = None, pagenum: int = 0, maxpages: int = 1, **kwargs):
        params = {"formInput": query, "pagenum": pagenum, "maxpages": maxpages}
        if doctype:
            params["doctypes"] = doctype
        params.update(kwargs)
        return await self.fetch("/search/", params=params)
