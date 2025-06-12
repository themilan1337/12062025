from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.api import router as auth_router
from celery_tasks import example_task, process_data, send_notification
from chat.api import router as chat_router
from database import get_async_db
from redis_client import test_redis_connection
from tasks.api import router as tasks_router

app = FastAPI()

app.include_router(auth_router, tags=["auth"])
app.include_router(chat_router, tags=["chat"])
app.include_router(tasks_router, tags=["tasks"])


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.get("/health")
async def check_health(db: AsyncSession = Depends(get_async_db)):
    try:
        await db.execute(text("SELECT 1"))
    except OperationalError:
        raise HTTPException(
            status_code=500, detail="Database connection failed"
        )

    # Check Redis connection
    redis_status = "connected" if test_redis_connection() else "disconnected"

    return {
        "status": "ok", 
        "database": "connected",
        "redis": redis_status
    }


@app.post("/tasks/example")
async def run_example_task(name: str):
    """Run an example Celery task"""
    task = example_task.delay(name)
    return {
        "task_id": task.id,
        "status": "Task queued",
        "message": f"Example task queued for {name}"
    }


@app.post("/tasks/notification")
async def send_notification_task(message: str, recipient: str):
    """Send a notification using Celery"""
    task = send_notification.delay(message, recipient)
    return {
        "task_id": task.id,
        "status": "Task queued",
        "message": f"Notification task queued for {recipient}"
    }


@app.post("/tasks/process")
async def process_data_task(data: dict):
    """Process data using Celery"""
    task = process_data.delay(data)
    return {
        "task_id": task.id,
        "status": "Task queued",
        "message": "Data processing task queued"
    }


@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Get the status of a Celery task"""
    from celery.result import AsyncResult

    from celery_app import celery_app
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }


@app.get("/chat-demo", response_class=HTMLResponse)
async def chat_demo():
    """Serve the chat demo page"""
    try:
        with open("src/chat/templates/chat.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
        <body>
        <h1>Chat Demo Not Found</h1>
        <p>The chat demo file could not be found. Please check the file path.</p>
        </body>
        </html>
        """, status_code=404)
