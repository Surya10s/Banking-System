from fastapi import APIRouter
from celery_worker import celery_app

router = APIRouter()


@router.get("/status/{task_id}")
def get_task_status(task_id: str):
    """Check the status of a scheduled transfer task."""
    task = celery_app.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task.state.lower()
    }
    
    if task.state == 'PENDING':
        response["message"] = "Transfer is scheduled and waiting to be executed"
    elif task.state == 'SUCCESS':
        response["result"] = task.result
    elif task.state == 'FAILURE':
        response["error"] = str(task.info)
    
    return response

