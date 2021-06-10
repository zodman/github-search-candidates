from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from config import USER, PAT, EXPIRE_CACHE
from asyncdiskcache import AsyncCache
import httpx
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

cache_search = AsyncCache()
cache_user = AsyncCache()
GH_URL="https://api.github.com"
auth = (USER,PAT)


async def process_response(resp, client):
    await cache_user.initialize(directory='/tmp/diskcache/cache_search_async')
    results = []
    items = resp.get("items")
    for u in items:
        url = u["url"]
        user = await cache_user.get(url)
        if not user:
            resp = await client.get(u["url"], auth=auth)
            resp.raise_for_status()
            user = resp.json()
            await cache_user.set(url, user, expire=EXPIRE_CACHE)
        results.append(user)
    return results

async def fetch(client, params):
    resp = await client.get(f"{GH_URL}/search/users", params=params, auth=auth)
    resp.raise_for_status()
    resp = resp.json()
    return resp

@app.get("/search")
async def search(s: str, location:str):
    await cache_search.initialize(directory='/tmp/diskcache/cache_user_async')
    client = httpx.AsyncClient()
    page=1
    if location !="":
        query = f"{s} location:{location}"
    else:
        query = s
    params = {
        'q':query,
        'per_page':99,
        'page':page
    }
    resp = await cache_search.get(query.lower())
    results = []
    if not resp:
        resp = await fetch(client, params)
        while resp and resp.get("items"):
            results_ = await process_response(resp, client)
            results.extend(results_)
            params["page"]+=1
            if params["page"]>5:
                break
            resp = await fetch(client, params)
        await cache_search.set(query.lower(), results)
    else:
        results = resp
    await client.aclose()
    return {'results': results, 'total': len(results)}


@app.get("/")
async def index(request:Request, response_class=HTMLResponse):
    return templates.TemplateResponse("index.html", {'request': request})
