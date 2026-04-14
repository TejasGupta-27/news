from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/model/info")
async def model_info():
    from app.services.classifier import classifier_service
    return {
        "version": classifier_service.model_version,
        "loaded": classifier_service.model is not None,
        "model_name": classifier_service.model_name,
    }
