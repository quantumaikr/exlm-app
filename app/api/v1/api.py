from fastapi import APIRouter

from app.api.v1.endpoints import health  # , auth, projects, models, datasets, websocket, roles, api_keys, hf_models, training, data_generation, data_preprocessing, data_quality, evaluation, versioning, serving
# from app.api.endpoints import quality_filter  # Temporarily disabled

api_router = APIRouter()

# Health check
api_router.include_router(health.router, prefix="/health", tags=["health"])

# # Auth
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# # Projects
# api_router.include_router(projects.router, prefix="/projects", tags=["projects"])

# # Models
# api_router.include_router(models.router, prefix="/models", tags=["models"])

# # Datasets
# api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])

# # WebSocket
# api_router.include_router(websocket.router, tags=["websocket"])

# # Roles and Permissions
# api_router.include_router(roles.router, prefix="/roles", tags=["roles"])

# Temporarily disabled due to User model dependency issues
# TODO: Fix User model imports and enable these endpoints

# # API Keys
# api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])

# # Hugging Face Models
# api_router.include_router(hf_models.router, prefix="/hf-models", tags=["hf-models"])

# # Training Jobs
# api_router.include_router(training.router, prefix="/training", tags=["training"])

# # Quality Filtering
# api_router.include_router(quality_filter.router, prefix="/quality-filter", tags=["quality-filter"])

# # Data Generation
# api_router.include_router(data_generation.router, prefix="/data-generation", tags=["data-generation"])

# # Data Preprocessing
# api_router.include_router(data_preprocessing.router, prefix="/data-preprocessing", tags=["data-preprocessing"])

# # Data Quality
# api_router.include_router(data_quality.router, prefix="/data-quality", tags=["data-quality"])

# # Model Evaluation
# api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])

# # Model Versioning
# api_router.include_router(versioning.router, prefix="/versioning", tags=["versioning"])

# # Model Serving
# api_router.include_router(serving.router, prefix="/serving", tags=["serving"])

# Future endpoints will be added here:
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
# api_router.include_router(deployments.router, prefix="/deployments", tags=["deployments"])