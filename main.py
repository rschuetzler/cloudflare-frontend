import os
import pprint

import CloudFlare
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

load_dotenv(find_dotenv())  # Load environment variables from .env file

TOKEN = os.getenv("CLOUDFLARE_TOKEN")
ZONE = os.getenv("CLOUDFLARE_ZONE")

app = FastAPI(debug=True)
templates = Jinja2Templates(directory="templates")

cf = CloudFlare.CloudFlare(token=TOKEN, raw=True)

# Remove this before deploying
pp = pprint.PrettyPrinter(indent=4)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, page: int = 1, q: str = None):
    per_page = 50
    params = {"per_page": per_page, "page": page}
    if q:
        params["name"] = q
        params["content"] = q
        params["match"] = "any"
    response = cf.zones.dns_records.get(
        ZONE,
        params=params,
    )
    total_records = int(response["result_info"]["total_count"])
    total_pages = (total_records + per_page - 1) // per_page
    page_obj = {
        "has_previous": page > 1,
        "has_next": page < total_pages,
        "previous_page_number": page - 1 if page > 1 else None,
        "next_page_number": page + 1 if page < total_pages else None,
        "number": page,
        "paginator": range(1, total_pages + 1),
    }
    dns_records = response["result"]
    for record in dns_records:
        record["edit_url"] = f"/edit/{record['id']}"
        record["delete_url"] = f"/delete/{record['id']}"

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "dns_records": dns_records, "page_obj": page_obj},
    )


@app.get("/create", response_class=HTMLResponse)
async def show_create_page(request: Request):
    return templates.TemplateResponse("new.html", {"request": request})


@app.post("/create")
async def create_dns_record(
    request: Request,
    name: str = Form(...),
    content: str = Form(...),
    type: str = Form(...),
    ttl: int = Form(...),
):
    response = cf.zones.dns_records.post(
        ZONE,
        data={
            "name": name,
            "content": content,
            "type": type,
            "ttl": ttl,
        },
    )
    print(response)

    return {"message": "DNS record created successfully"}


@app.get("/edit/{record_id}", response_class=HTMLResponse)
async def edit_dns_record(request: Request, record_id: str):
    response = cf.zones.dns_records.get(
        ZONE,
        record_id,
    )
    dns_record = response["result"]

    return templates.TemplateResponse(
        "edit.html",
        {"request": request, "record": dns_record},
    )


@app.post("/edit/{record_id}")
async def update_dns_record(
    request: Request,
    record_id: str,
    name: str = Form(...),
    content: str = Form(...),
    type: str = Form(...),
    ttl: int = Form(...),
):
    response = cf.zones.dns_records.put(
        ZONE,
        record_id,
        data={
            "name": name,
            "content": content,
            "type": type,
            "ttl": ttl,
        },
    )

    return {"message": "DNS record updated successfully"}


@app.get("/delete/{record_id}")
async def delete_dns_record(request: Request, record_id: str):
    response = cf.zones.dns_records.delete(
        ZONE,
        record_id,
    )

    return {"message": "DNS record deleted successfully"}
