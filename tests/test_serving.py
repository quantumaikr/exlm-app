"""
모델 서빙 API 테스트
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.model import Model, ModelStatus
from app.models.project import Project
from app.models.user import User
from app.schemas.serving import ServingConfig, GenerationRequest


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    return User(
        id="test-user-id",
        email="test@example.com",
        username="testuser",
        is_active=True
    )


@pytest.fixture
def mock_project():
    return Project(
        id="test-project-id",
        name="Test Project",
        description="Test project description",
        user_id="test-user-id"
    )


@pytest.fixture
def mock_model():
    return Model(
        id="test-model-id",
        name="Test Model",
        project_id="test-project-id",
        status=ModelStatus.READY,
        model_path="/tmp/test-model",
        model_type="llama2"
    )


@pytest.fixture
def serving_config():
    return ServingConfig(
        max_model_len=2048,
        gpu_memory_utilization=0.9,
        max_num_batched_tokens=4096,
        max_num_seqs=256,
        tensor_parallel_size=1,
        trust_remote_code=False,
        dtype="auto"
    )


@pytest.fixture
def generation_request():
    return GenerationRequest(
        prompt="Hello, how are you?",
        max_tokens=100,
        temperature=0.7,
        top_p=0.9
    )


class TestModelServing:
    """모델 서빙 API 테스트"""
    
    @patch('app.api.v1.endpoints.serving.get_current_active_user')
    @patch('app.api.v1.endpoints.serving.get_db')
    @patch('app.api.v1.endpoints.serving.model_serving_service')
    async def test_start_model_serving(
        self,
        mock_serving_service,
        mock_get_db,
        mock_get_current_user,
        client,
        mock_user,
        mock_project,
        mock_model,
        serving_config
    ):
        """모델 서빙 시작 테스트"""
        # Mock 설정
        mock_get_current_user.return_value = mock_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # DB 조회 결과 설정
        mock_db.get.side_effect = lambda model, id: {
            "test-model-id": mock_model,
            "test-project-id": mock_project
        }.get(str(id))
        
        # 서빙 서비스 Mock
        mock_serving_info = {
            "model_id": "test-model-id",
            "status": "running",
            "endpoint_url": "http://localhost:8001",
            "config": serving_config.dict(),
            "started_at": "2024-01-08T10:00:00Z"
        }
        mock_serving_service.start_serving.return_value = mock_serving_info
        
        # API 호출
        response = client.post(
            "/api/v1/serving/models/test-model-id/serve",
            json=serving_config.dict(),
            headers={"Authorization": "Bearer test-token"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "test-model-id"
        assert data["status"] == "running"
        assert "endpoint_url" in data
    
    @patch('app.api.v1.endpoints.serving.get_current_active_user')
    @patch('app.api.v1.endpoints.serving.get_db')
    @patch('app.api.v1.endpoints.serving.model_serving_service')
    async def test_get_serving_status(
        self,
        mock_serving_service,
        mock_get_db,
        mock_get_current_user,
        client,
        mock_user,
        mock_project,
        mock_model
    ):
        """서빙 상태 조회 테스트"""
        # Mock 설정
        mock_get_current_user.return_value = mock_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # DB 조회 결과 설정
        mock_db.get.side_effect = lambda model, id: {
            "test-model-id": mock_model,
            "test-project-id": mock_project
        }.get(str(id))
        
        # 서빙 서비스 Mock
        mock_serving_info = {
            "model_id": "test-model-id",
            "status": "running",
            "endpoint_url": "http://localhost:8001"
        }
        mock_serving_service.get_serving_status.return_value = mock_serving_info
        
        # API 호출
        response = client.get(
            "/api/v1/serving/models/test-model-id/serve",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "test-model-id"
        assert data["status"] == "running"
    
    @patch('app.api.v1.endpoints.serving.get_current_active_user')
    @patch('app.api.v1.endpoints.serving.get_db')
    @patch('app.api.v1.endpoints.serving.model_serving_service')
    async def test_stop_model_serving(
        self,
        mock_serving_service,
        mock_get_db,
        mock_get_current_user,
        client,
        mock_user,
        mock_project,
        mock_model
    ):
        """모델 서빙 중지 테스트"""
        # Mock 설정
        mock_get_current_user.return_value = mock_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # DB 조회 결과 설정
        mock_db.get.side_effect = lambda model, id: {
            "test-model-id": mock_model,
            "test-project-id": mock_project
        }.get(str(id))
        
        # 서빙 서비스 Mock
        mock_serving_service.stop_serving.return_value = None
        
        # API 호출
        response = client.delete(
            "/api/v1/serving/models/test-model-id/serve",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    @patch('app.api.v1.endpoints.serving.get_current_active_user')
    @patch('app.api.v1.endpoints.serving.get_db')
    @patch('app.api.v1.endpoints.serving.model_serving_service')
    async def test_generate_text(
        self,
        mock_serving_service,
        mock_get_db,
        mock_get_current_user,
        client,
        mock_user,
        mock_project,
        mock_model,
        generation_request
    ):
        """텍스트 생성 테스트"""
        # Mock 설정
        mock_get_current_user.return_value = mock_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # 모델 상태를 SERVING으로 설정
        mock_model.status = ModelStatus.SERVING
        
        # DB 조회 결과 설정
        mock_db.get.side_effect = lambda model, id: {
            "test-model-id": mock_model,
            "test-project-id": mock_project
        }.get(str(id))
        
        # 서빙 서비스 Mock
        mock_generation_result = {
            "text": "I'm doing well, thank you!",
            "tokens_used": 10,
            "finish_reason": "stop",
            "latency": 0.5
        }
        mock_serving_service.generate_text.return_value = mock_generation_result
        
        # API 호출
        response = client.post(
            "/api/v1/serving/models/test-model-id/generate",
            json=generation_request.dict(),
            headers={"Authorization": "Bearer test-token"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "I'm doing well, thank you!"
        assert data["tokens_used"] == 10
        assert data["finish_reason"] == "stop"
    
    @patch('app.api.v1.endpoints.serving.get_current_active_user')
    @patch('app.api.v1.endpoints.serving.model_serving_service')
    async def test_list_serving_models(
        self,
        mock_serving_service,
        mock_get_current_user,
        client,
        mock_user
    ):
        """서빙 중인 모델 목록 조회 테스트"""
        # Mock 설정
        mock_get_current_user.return_value = mock_user
        
        # 서빙 서비스 Mock
        mock_serving_models = [
            {
                "model_id": "test-model-1",
                "status": "running",
                "endpoint_url": "http://localhost:8001"
            },
            {
                "model_id": "test-model-2",
                "status": "running",
                "endpoint_url": "http://localhost:8002"
            }
        ]
        mock_serving_service.list_serving_models.return_value = mock_serving_models
        
        # API 호출
        response = client.get(
            "/api/v1/serving/serving/models",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["model_id"] == "test-model-1"
        assert data[1]["model_id"] == "test-model-2"
    
    @patch('app.api.v1.endpoints.serving.get_current_active_user')
    @patch('app.api.v1.endpoints.serving.get_db')
    @patch('app.api.v1.endpoints.serving.model_serving_service')
    async def test_get_serving_metrics(
        self,
        mock_serving_service,
        mock_get_db,
        mock_get_current_user,
        client,
        mock_user,
        mock_project,
        mock_model
    ):
        """서빙 메트릭 조회 테스트"""
        # Mock 설정
        mock_get_current_user.return_value = mock_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # DB 조회 결과 설정
        mock_db.get.side_effect = lambda model, id: {
            "test-model-id": mock_model,
            "test-project-id": mock_project
        }.get(str(id))
        
        # 서빙 서비스 Mock
        mock_metrics = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "average_latency": 0.5,
            "tokens_per_second": 100.0
        }
        mock_serving_service.get_model_metrics.return_value = mock_metrics
        
        # API 호출
        response = client.get(
            "/api/v1/serving/serving/metrics?model_id=test-model-id",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 100
        assert data["successful_requests"] == 95
        assert data["average_latency"] == 0.5


class TestServingConfig:
    """서빙 설정 테스트"""
    
    def test_serving_config_defaults(self):
        """기본 서빙 설정 테스트"""
        config = ServingConfig()
        
        assert config.max_model_len == 2048
        assert config.gpu_memory_utilization == 0.9
        assert config.max_num_batched_tokens == 4096
        assert config.max_num_seqs == 256
        assert config.tensor_parallel_size == 1
        assert config.trust_remote_code is False
        assert config.dtype == "auto"
    
    def test_serving_config_custom(self):
        """커스텀 서빙 설정 테스트"""
        config = ServingConfig(
            max_model_len=4096,
            gpu_memory_utilization=0.8,
            tensor_parallel_size=2,
            trust_remote_code=True
        )
        
        assert config.max_model_len == 4096
        assert config.gpu_memory_utilization == 0.8
        assert config.tensor_parallel_size == 2
        assert config.trust_remote_code is True


class TestGenerationRequest:
    """텍스트 생성 요청 테스트"""
    
    def test_generation_request_defaults(self):
        """기본 생성 요청 테스트"""
        request = GenerationRequest(prompt="Hello")
        
        assert request.prompt == "Hello"
        assert request.max_tokens == 512
        assert request.temperature == 0.7
        assert request.top_p == 0.9
        assert request.stream is False
        assert request.stop is None
    
    def test_generation_request_custom(self):
        """커스텀 생성 요청 테스트"""
        request = GenerationRequest(
            prompt="Hello",
            max_tokens=100,
            temperature=0.5,
            top_p=0.8,
            stop=["\n", "."]
        )
        
        assert request.prompt == "Hello"
        assert request.max_tokens == 100
        assert request.temperature == 0.5
        assert request.top_p == 0.8
        assert request.stop == ["\n", "."] 