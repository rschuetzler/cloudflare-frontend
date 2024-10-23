import logging
import os
import secrets

import CloudFlare
from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

load_dotenv(find_dotenv())  # Load environment variables from .env file

TOKEN = os.getenv("CLOUDFLARE_TOKEN")
ZONE = os.getenv("CLOUDFLARE_ZONE")
USERNAME = os.getenv("BASIC_AUTH_USERNAME")
PASSWORD = os.getenv("BASIC_AUTH_PASSWORD")

print(TOKEN, ZONE, USERNAME, PASSWORD)

app = FastAPI(debug=True)
templates = Jinja2Templates(directory="templates")

cf = CloudFlare.CloudFlare(token=TOKEN, raw=True)

security = HTTPBasic()

# Configure logging
log_file_path = "app.log"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()])
logger = logging.getLogger(__name__)


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
            )
        

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, page: int = 1, q: str = None, credentials: HTTPBasicCredentials = Depends(verify_credentials)):
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
    # print(dns_records)
    for record in dns_records:
        record["edit_url"] = f"/edit/{record['id']}"
        record["delete_url"] = f"/delete/{record['id']}"

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "dns_records": dns_records, "page_obj": page_obj},
    )


@app.get("/create", response_class=HTMLResponse )
async def show_create_page(request: Request):
    return templates.TemplateResponse("new.html", {"request": request})


@app.post("/create")
async def create_dns_record(
    request: Request,
    name: str = Form(...),
    content: str = Form(...),
    type: str = Form(...),
    ttl: int = Form(...),
     credentials: HTTPBasicCredentials = Depends(verify_credentials)
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

    client_ip = request.client.host
    logger.info(f"CREATE  - Record created by {client_ip}: name={name}, type={type}")

    return {"message": "DNS record created successfully"}


@app.get("/edit/{record_id}", response_class=HTMLResponse)
async def edit_dns_record(request: Request, record_id: str, credentials: HTTPBasicCredentials = Depends(verify_credentials)):
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
    ttl: int = Form(...), credentials: HTTPBasicCredentials = Depends(verify_credentials)
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
    
    client_ip = request.client.host
    logger.info(f"EDIT   - Record updated by {client_ip}: name={name}, type={type}")

    return {"message": "DNS record updated successfully"}


@app.get("/delete/{record_id}")
async def delete_dns_record(request: Request, record_id: str, credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    response = cf.zones.dns_records.delete(
        ZONE,
        record_id,
    )

    client_ip = request.client.host
    logger.info(f"DELETE - Record deleted by {client_ip}: {record_id}")

    return {"message": "DNS record deleted successfully"}
