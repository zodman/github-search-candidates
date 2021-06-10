from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse as StreamResponse
from config import USER, PAT, EXPIRE_CACHE
from asyncdiskcache import AsyncCache
import httpx
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import aiofiles.tempfile
from aiocsv import AsyncDictWriter


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

import os

async def csv_results(results, query):
    filepath = None
    headers = ["name", "bio", "email", "company", "html_url", "location", "hireable"]
    def filterit(r):
        keys = r.keys()
        for k in list(keys):
            if k not in headers:
                r.pop(k, None)
        return r
    results = map(filterit, results)
    async with aiofiles.tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "out.csv")
        async with aiofiles.open(filepath,mode="w", newline="", encoding="utf-8") as f:
            writer = AsyncDictWriter(f, dialect="unix", fieldnames=headers)
            await writer.writeheader()
            await writer.writerows(results)
            return StreamResponse(open(filepath), media_type="text/csv", 
                                  headers={
                                                  "Content-Disposition": f"attachment;filename={query}.csv"
                                              })

@app.get("/search")
async def search(s: str, location:str, csv: str):
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
    if csv !="":
        return await csv_results(results, query)
    return {'results': results, 'total': len(results)}


@app.get("/")
async def index(request:Request, response_class=HTMLResponse):
    return templates.TemplateResponse("index.html", {'request': request})
