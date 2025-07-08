from typing import List, Dict, Optional, Any
import httpx
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache
from app.core.config import settings
from app.core.logging import get_logger
from app.models.model import ModelProvider
import json

logger = get_logger(__name__)

class HuggingFaceService:
    """Hugging Face Model Hub 연동 서비스"""
    
    BASE_URL = "https://huggingface.co/api"
    MODELS_ENDPOINT = f"{BASE_URL}/models"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._cache = {}
        self._cache_expiry = {}
        self.cache_duration = timedelta(hours=1)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _is_cache_valid(self, key: str) -> bool:
        """캐시가 유효한지 확인"""
        if key not in self._cache_expiry:
            return False
        return datetime.utcnow() < self._cache_expiry[key]
    
    def _set_cache(self, key: str, value: Any):
        """캐시 설정"""
        self._cache[key] = value
        self._cache_expiry[key] = datetime.utcnow() + self.cache_duration
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """캐시 가져오기"""
        if self._is_cache_valid(key):
            return self._cache[key]
        return None
    
    async def search_models(
        self,
        query: Optional[str] = None,
        task: Optional[str] = None,
        library: Optional[str] = None,
        language: Optional[str] = None,
        sort: str = "trending",
        limit: int = 50,
        full: bool = True
    ) -> List[Dict[str, Any]]:
        """Hugging Face에서 모델 검색"""
        
        # 캐시 키 생성
        cache_key = f"search:{query}:{task}:{library}:{language}:{sort}:{limit}"
        cached_result = self._get_cache(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            "sort": sort,
            "limit": limit,
            "full": str(full).lower()
        }
        
        if query:
            params["search"] = query
        if task:
            params["filter"] = task
        if library:
            params["library"] = library
        if language:
            params["language"] = language
        
        try:
            response = await self.client.get(self.MODELS_ENDPOINT, params=params)
            response.raise_for_status()
            
            models = response.json()
            
            # 모델 정보 정제
            processed_models = []
            for model in models:
                processed_model = self._process_model_data(model)
                if processed_model:
                    processed_models.append(processed_model)
            
            # 캐시 저장
            self._set_cache(cache_key, processed_models)
            
            return processed_models
            
        except httpx.HTTPError as e:
            logger.error(f"Hugging Face API 호출 실패: {e}")
            return []
    
    async def get_model_details(self, model_id: str) -> Optional[Dict[str, Any]]:
        """특정 모델의 상세 정보 가져오기"""
        
        cache_key = f"model:{model_id}"
        cached_result = self._get_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            response = await self.client.get(f"{self.MODELS_ENDPOINT}/{model_id}")
            response.raise_for_status()
            
            model_data = response.json()
            processed_model = self._process_model_data(model_data, detailed=True)
            
            # 캐시 저장
            if processed_model:
                self._set_cache(cache_key, processed_model)
            
            return processed_model
            
        except httpx.HTTPError as e:
            logger.error(f"모델 정보 가져오기 실패 {model_id}: {e}")
            return None
    
    async def get_model_files(self, model_id: str) -> List[Dict[str, Any]]:
        """모델 파일 목록 가져오기"""
        
        cache_key = f"files:{model_id}"
        cached_result = self._get_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            response = await self.client.get(f"{self.MODELS_ENDPOINT}/{model_id}/tree/main")
            response.raise_for_status()
            
            files = response.json()
            
            # 파일 정보 정제
            processed_files = []
            for file in files:
                if file.get("type") == "file":
                    processed_files.append({
                        "path": file.get("path"),
                        "size": file.get("size"),
                        "lfs": file.get("lfs", {}),
                    })
            
            # 캐시 저장
            self._set_cache(cache_key, processed_files)
            
            return processed_files
            
        except httpx.HTTPError as e:
            logger.error(f"모델 파일 목록 가져오기 실패 {model_id}: {e}")
            return []
    
    async def get_trending_models(
        self,
        task: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """트렌딩 모델 가져오기"""
        
        return await self.search_models(
            task=task,
            sort="trending",
            limit=limit
        )
    
    async def get_model_by_task(self, task: str, limit: int = 20) -> List[Dict[str, Any]]:
        """특정 태스크에 적합한 모델 가져오기"""
        
        task_mapping = {
            "text-generation": "text-generation",
            "text2text-generation": "text2text-generation",
            "conversational": "conversational",
            "question-answering": "question-answering",
            "summarization": "summarization",
            "translation": "translation",
        }
        
        hf_task = task_mapping.get(task, task)
        return await self.search_models(task=hf_task, limit=limit)
    
    def _process_model_data(self, model: Dict[str, Any], detailed: bool = False) -> Optional[Dict[str, Any]]:
        """모델 데이터 처리 및 정제"""
        
        try:
            # 기본 정보
            processed = {
                "id": model.get("id", ""),
                "name": model.get("id", "").split("/")[-1],
                "full_name": model.get("id", ""),
                "author": model.get("id", "").split("/")[0] if "/" in model.get("id", "") else "",
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0),
                "trending_score": self._calculate_trending_score(model),
                "created_at": model.get("created_at", ""),
                "updated_at": model.get("lastModified", ""),
                "private": model.get("private", False),
                "tags": model.get("tags", []),
                "pipeline_tag": model.get("pipeline_tag", ""),
                "library_name": model.get("library_name", ""),
            }
            
            # 모델 크기 추정
            processed["size"] = self._estimate_model_size(model)
            processed["parameters"] = self._extract_parameters(model)
            
            # 라이선스 정보
            processed["license"] = self._extract_license(model)
            
            # 설명
            processed["description"] = self._extract_description(model)
            
            # 상세 정보 (옵션)
            if detailed:
                processed["model_index"] = model.get("model-index", {})
                processed["config"] = model.get("config", {})
                processed["card_data"] = model.get("cardData", {})
                processed["siblings"] = model.get("siblings", [])
                
                # 성능 메트릭 추출
                processed["performance_metrics"] = self._extract_performance_metrics(model)
                
                # 요구사항 추출
                processed["requirements"] = self._extract_requirements(model)
            
            # 프로바이더 결정
            processed["provider"] = self._determine_provider(model)
            
            return processed
            
        except Exception as e:
            logger.error(f"모델 데이터 처리 실패: {e}")
            return None
    
    def _calculate_trending_score(self, model: Dict[str, Any]) -> float:
        """트렌딩 스코어 계산"""
        downloads = model.get("downloads", 0)
        likes = model.get("likes", 0)
        
        # 최근 업데이트 가중치
        last_modified = model.get("lastModified", "")
        if last_modified:
            try:
                last_update = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
                days_since_update = (datetime.utcnow() - last_update.replace(tzinfo=None)).days
                recency_factor = max(0, 1 - (days_since_update / 365))
            except:
                recency_factor = 0.5
        else:
            recency_factor = 0.5
        
        # 트렌딩 스코어 계산 (0-100)
        score = min(100, (
            (downloads / 1000) * 0.3 +
            (likes / 100) * 0.3 +
            recency_factor * 40
        ))
        
        return round(score, 1)
    
    def _estimate_model_size(self, model: Dict[str, Any]) -> str:
        """모델 크기 추정"""
        model_id = model.get("id", "").lower()
        
        # 모델 이름에서 크기 추출
        size_patterns = {
            "3b": "3B", "3.8b": "3.8B", "7b": "7B", "8b": "8B",
            "13b": "13B", "14b": "14B", "30b": "30B", "34b": "34B",
            "40b": "40B", "65b": "65B", "70b": "70B", "72b": "72B",
            "175b": "175B", "540b": "540B"
        }
        
        for pattern, size in size_patterns.items():
            if pattern in model_id:
                return size
        
        # 태그에서 크기 추출
        tags = model.get("tags", [])
        for tag in tags:
            for pattern, size in size_patterns.items():
                if pattern in tag.lower():
                    return size
        
        return "Unknown"
    
    def _extract_parameters(self, model: Dict[str, Any]) -> str:
        """파라미터 수 추출"""
        size = self._estimate_model_size(model)
        if size != "Unknown":
            return f"{size} parameters"
        return "Unknown parameters"
    
    def _extract_license(self, model: Dict[str, Any]) -> str:
        """라이선스 정보 추출"""
        # 태그에서 라이선스 찾기
        tags = model.get("tags", [])
        license_tags = [tag for tag in tags if tag.startswith("license:")]
        if license_tags:
            return license_tags[0].replace("license:", "")
        
        # 카드 데이터에서 찾기
        card_data = model.get("cardData", {})
        if isinstance(card_data, dict):
            license_info = card_data.get("license", "")
            if license_info:
                return license_info
        
        return "Unknown"
    
    def _extract_description(self, model: Dict[str, Any]) -> str:
        """모델 설명 추출"""
        # 카드 데이터에서 설명 찾기
        card_data = model.get("cardData", {})
        if isinstance(card_data, dict):
            # 여러 필드에서 설명 찾기
            for field in ["description", "model_description", "abstract"]:
                desc = card_data.get(field, "")
                if desc:
                    return desc[:500]  # 최대 500자
        
        # 태그 기반 설명 생성
        tags = model.get("tags", [])
        pipeline_tag = model.get("pipeline_tag", "")
        
        if pipeline_tag:
            desc = f"A {pipeline_tag} model"
            if tags:
                desc += f" with tags: {', '.join(tags[:5])}"
            return desc
        
        return "No description available"
    
    def _extract_performance_metrics(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """성능 메트릭 추출"""
        metrics = {
            "inference_speed": 75,  # 기본값
            "memory_usage": self._estimate_memory_usage(model),
            "accuracy_score": 85,  # 기본값
        }
        
        # 모델 인덱스에서 메트릭 찾기
        model_index = model.get("model-index", [])
        if isinstance(model_index, list):
            for entry in model_index:
                results = entry.get("results", [])
                if isinstance(results, list):
                    for result in results:
                        metrics_data = result.get("metrics", [])
                        if isinstance(metrics_data, list):
                            for metric in metrics_data:
                                if metric.get("type") == "accuracy":
                                    metrics["accuracy_score"] = metric.get("value", 85) * 100
        
        return metrics
    
    def _estimate_memory_usage(self, model: Dict[str, Any]) -> float:
        """메모리 사용량 추정 (GB)"""
        size = self._estimate_model_size(model)
        
        memory_map = {
            "3B": 6, "3.8B": 8, "7B": 14, "8B": 16,
            "13B": 26, "14B": 28, "30B": 60, "34B": 68,
            "40B": 80, "65B": 130, "70B": 140, "72B": 144,
            "175B": 350, "540B": 1080
        }
        
        return memory_map.get(size, 10)
    
    def _extract_requirements(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """시스템 요구사항 추출"""
        memory_usage = self._estimate_memory_usage(model)
        
        # GPU 추천
        if memory_usage <= 8:
            recommended_gpu = "RTX 3060 or better"
        elif memory_usage <= 16:
            recommended_gpu = "RTX 3090 or better"
        elif memory_usage <= 40:
            recommended_gpu = "A100 40GB or better"
        elif memory_usage <= 80:
            recommended_gpu = "A100 80GB or better"
        else:
            recommended_gpu = "Multiple A100 80GB GPUs"
        
        return {
            "min_gpu_memory": int(memory_usage),
            "recommended_gpu": recommended_gpu,
            "disk_space": int(memory_usage * 2.5),  # 모델 + 체크포인트 + 여유 공간
        }
    
    def _determine_provider(self, model: Dict[str, Any]) -> ModelProvider:
        """모델 제공자 결정"""
        model_id = model.get("id", "").lower()
        
        provider_mapping = {
            "meta-llama": ModelProvider.META,
            "mistralai": ModelProvider.MISTRAL,
            "microsoft": ModelProvider.MICROSOFT,
            "google": ModelProvider.GOOGLE,
            "alibaba": ModelProvider.ALIBABA,
            "baichuan": ModelProvider.BAICHUAN,
            "01-ai": ModelProvider.YI,
            "tiiuae": ModelProvider.FALCON,
            "bigscience": ModelProvider.BIGSCIENCE,
            "eleutherai": ModelProvider.ELEUTHERAI,
        }
        
        for key, provider in provider_mapping.items():
            if model_id.startswith(key):
                return provider
        
        return ModelProvider.COMMUNITY


# 싱글톤 인스턴스
huggingface_service = HuggingFaceService()