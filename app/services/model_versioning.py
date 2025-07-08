"""
모델 버전 관리 서비스
"""
import os
import json
import shutil
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.models.model import Model, ModelVersion, ModelStatus
from app.models.user import User
from app.core.storage import storage_service
import git


class ModelVersioningService:
    """모델 버전 관리 서비스"""
    
    def __init__(self):
        self.base_path = Path(settings.MODEL_STORAGE_PATH)
        self.version_control_enabled = True
        self._init_git_repo()
    
    def _init_git_repo(self):
        """Git 저장소 초기화"""
        try:
            if not (self.base_path / ".git").exists():
                self.repo = git.Repo.init(self.base_path)
                logger.info(f"Initialized git repository at {self.base_path}")
            else:
                self.repo = git.Repo(self.base_path)
        except Exception as e:
            logger.warning(f"Git initialization failed: {e}")
            self.version_control_enabled = False
    
    async def create_model_version(
        self,
        db: AsyncSession,
        model_id: UUID,
        version_tag: str,
        description: Optional[str] = None,
        training_job_id: Optional[UUID] = None,
        metrics: Optional[Dict[str, Any]] = None,
        user_id: UUID = None
    ) -> ModelVersion:
        """새 모델 버전 생성"""
        # 모델 조회
        model = await db.get(Model, model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        # 버전 태그 유효성 검사
        existing = await self._check_version_exists(db, model_id, version_tag)
        if existing:
            raise ValueError(f"Version {version_tag} already exists for model {model_id}")
        
        # 모델 파일 해시 계산
        model_hash = await self._calculate_model_hash(model.path)
        
        # 버전 디렉토리 생성
        version_path = await self._create_version_directory(model, version_tag)
        
        # 모델 파일 복사
        await self._copy_model_files(model.path, version_path)
        
        # 버전 메타데이터 생성
        metadata = {
            "model_id": str(model_id),
            "version": version_tag,
            "created_at": datetime.utcnow().isoformat(),
            "model_hash": model_hash,
            "base_model": model.base_model,
            "training_method": model.training_method,
            "training_config": model.config,
            "metrics": metrics
        }
        
        # 메타데이터 저장
        metadata_path = version_path / "version_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Git 커밋 (활성화된 경우)
        commit_hash = None
        if self.version_control_enabled:
            commit_hash = await self._git_commit_version(version_path, version_tag, description)
        
        # 데이터베이스에 버전 레코드 생성
        version = ModelVersion(
            id=uuid4(),
            model_id=model_id,
            version=version_tag,
            description=description,
            path=str(version_path),
            model_hash=model_hash,
            commit_hash=commit_hash,
            training_job_id=training_job_id,
            metrics=metrics,
            metadata=metadata,
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        
        db.add(version)
        
        # 모델의 최신 버전 업데이트
        model.latest_version = version_tag
        model.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(version)
        
        logger.info(f"Created version {version_tag} for model {model_id}")
        return version
    
    async def list_model_versions(
        self,
        db: AsyncSession,
        model_id: UUID,
        include_metrics: bool = True
    ) -> List[ModelVersion]:
        """모델의 모든 버전 조회"""
        query = select(ModelVersion).where(ModelVersion.model_id == model_id)
        query = query.order_by(ModelVersion.created_at.desc())
        
        result = await db.execute(query)
        versions = result.scalars().all()
        
        if not include_metrics:
            # 메트릭 정보 제외
            for version in versions:
                version.metrics = None
        
        return versions
    
    async def get_model_version(
        self,
        db: AsyncSession,
        model_id: UUID,
        version: str
    ) -> Optional[ModelVersion]:
        """특정 버전 조회"""
        query = select(ModelVersion).where(
            and_(
                ModelVersion.model_id == model_id,
                ModelVersion.version == version
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def compare_versions(
        self,
        db: AsyncSession,
        model_id: UUID,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """두 버전 비교"""
        v1 = await self.get_model_version(db, model_id, version1)
        v2 = await self.get_model_version(db, model_id, version2)
        
        if not v1 or not v2:
            raise ValueError("One or both versions not found")
        
        comparison = {
            "model_id": str(model_id),
            "versions": {
                "v1": version1,
                "v2": version2
            },
            "timestamps": {
                "v1": v1.created_at.isoformat(),
                "v2": v2.created_at.isoformat()
            },
            "file_changes": {
                "hash_changed": v1.model_hash != v2.model_hash
            },
            "metric_comparison": self._compare_metrics(v1.metrics, v2.metrics),
            "config_changes": self._compare_configs(v1.metadata, v2.metadata)
        }
        
        # Git diff (활성화된 경우)
        if self.version_control_enabled and v1.commit_hash and v2.commit_hash:
            comparison["git_diff"] = await self._get_git_diff(v1.commit_hash, v2.commit_hash)
        
        return comparison
    
    async def rollback_to_version(
        self,
        db: AsyncSession,
        model_id: UUID,
        version: str,
        user_id: UUID
    ) -> Model:
        """특정 버전으로 롤백"""
        # 버전 조회
        version_obj = await self.get_model_version(db, model_id, version)
        if not version_obj:
            raise ValueError(f"Version {version} not found")
        
        # 모델 조회
        model = await db.get(Model, model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        # 현재 모델 백업
        backup_version = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        await self.create_model_version(
            db, model_id, backup_version,
            description=f"Automatic backup before rollback to {version}",
            user_id=user_id
        )
        
        # 버전 파일을 현재 모델 경로로 복사
        await self._copy_model_files(version_obj.path, model.path)
        
        # 모델 정보 업데이트
        model.latest_version = version
        model.updated_at = datetime.utcnow()
        
        # 롤백 기록
        rollback_info = {
            "action": "rollback",
            "from_version": backup_version,
            "to_version": version,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(user_id)
        }
        
        if not model.metadata:
            model.metadata = {}
        model.metadata["last_rollback"] = rollback_info
        
        await db.commit()
        await db.refresh(model)
        
        logger.info(f"Rolled back model {model_id} to version {version}")
        return model
    
    async def delete_version(
        self,
        db: AsyncSession,
        model_id: UUID,
        version: str,
        force: bool = False
    ) -> None:
        """버전 삭제"""
        version_obj = await self.get_model_version(db, model_id, version)
        if not version_obj:
            raise ValueError(f"Version {version} not found")
        
        # 최신 버전인지 확인
        model = await db.get(Model, model_id)
        if model and model.latest_version == version and not force:
            raise ValueError("Cannot delete the latest version without force flag")
        
        # 파일 삭제
        version_path = Path(version_obj.path)
        if version_path.exists():
            shutil.rmtree(version_path)
        
        # 데이터베이스에서 삭제
        await db.delete(version_obj)
        await db.commit()
        
        logger.info(f"Deleted version {version} of model {model_id}")
    
    async def export_version(
        self,
        db: AsyncSession,
        model_id: UUID,
        version: str,
        export_format: str = "huggingface",
        output_path: Optional[str] = None
    ) -> str:
        """버전 내보내기"""
        version_obj = await self.get_model_version(db, model_id, version)
        if not version_obj:
            raise ValueError(f"Version {version} not found")
        
        # 출력 경로 설정
        if not output_path:
            export_dir = self.base_path / "exports"
            export_dir.mkdir(exist_ok=True)
            output_path = export_dir / f"model_{model_id}_v{version}_{export_format}"
        else:
            output_path = Path(output_path)
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        if export_format == "huggingface":
            # HuggingFace 형식으로 내보내기
            await self._export_huggingface_format(version_obj.path, output_path)
        elif export_format == "onnx":
            # ONNX 형식으로 변환 및 내보내기
            await self._export_onnx_format(version_obj.path, output_path)
        elif export_format == "archive":
            # 압축 파일로 내보내기
            await self._export_archive_format(version_obj.path, output_path)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        logger.info(f"Exported version {version} to {output_path}")
        return str(output_path)
    
    async def _check_version_exists(
        self,
        db: AsyncSession,
        model_id: UUID,
        version: str
    ) -> bool:
        """버전 존재 여부 확인"""
        query = select(ModelVersion).where(
            and_(
                ModelVersion.model_id == model_id,
                ModelVersion.version == version
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def _calculate_model_hash(self, model_path: str) -> str:
        """모델 파일 해시 계산"""
        hasher = hashlib.sha256()
        model_files = []
        
        path = Path(model_path)
        if path.is_dir():
            # 디렉토리의 경우 주요 파일들의 해시 계산
            for file_pattern in ["*.bin", "*.safetensors", "*.pt", "*.pth"]:
                model_files.extend(path.glob(file_pattern))
        else:
            model_files = [path]
        
        for file_path in sorted(model_files):
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
        
        return hasher.hexdigest()
    
    async def _create_version_directory(
        self,
        model: Model,
        version: str
    ) -> Path:
        """버전 디렉토리 생성"""
        version_base = self.base_path / "versions" / str(model.id)
        version_path = version_base / version
        version_path.mkdir(parents=True, exist_ok=True)
        return version_path
    
    async def _copy_model_files(self, src: str, dst: str) -> None:
        """모델 파일 복사"""
        src_path = Path(src)
        dst_path = Path(dst)
        
        if src_path.is_dir():
            # 디렉토리 전체 복사
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
        else:
            # 단일 파일 복사
            shutil.copy2(src_path, dst_path)
    
    async def _git_commit_version(
        self,
        version_path: Path,
        version_tag: str,
        description: Optional[str]
    ) -> Optional[str]:
        """Git 커밋 생성"""
        try:
            # 파일 추가
            self.repo.index.add([str(version_path.relative_to(self.base_path))])
            
            # 커밋 메시지 생성
            commit_message = f"Model version {version_tag}"
            if description:
                commit_message += f"\n\n{description}"
            
            # 커밋
            commit = self.repo.index.commit(commit_message)
            
            # 태그 생성
            self.repo.create_tag(f"v{version_tag}", ref=commit)
            
            return commit.hexsha
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return None
    
    async def _get_git_diff(self, commit1: str, commit2: str) -> Dict[str, Any]:
        """Git diff 조회"""
        try:
            diff = self.repo.git.diff(commit1, commit2, "--stat")
            return {
                "summary": diff,
                "commits": [commit1, commit2]
            }
        except Exception as e:
            logger.error(f"Git diff failed: {e}")
            return {}
    
    def _compare_metrics(
        self,
        metrics1: Optional[Dict[str, Any]],
        metrics2: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """메트릭 비교"""
        if not metrics1 or not metrics2:
            return {"available": False}
        
        comparison = {"available": True, "changes": {}}
        
        all_keys = set(metrics1.keys()) | set(metrics2.keys())
        for key in all_keys:
            val1 = metrics1.get(key)
            val2 = metrics2.get(key)
            
            if val1 != val2:
                comparison["changes"][key] = {
                    "v1": val1,
                    "v2": val2,
                    "change": val2 - val1 if isinstance(val1, (int, float)) and isinstance(val2, (int, float)) else None
                }
        
        return comparison
    
    def _compare_configs(
        self,
        config1: Optional[Dict[str, Any]],
        config2: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """설정 비교"""
        if not config1 or not config2:
            return {"available": False}
        
        changes = {}
        
        # 학습 설정 비교
        for key in ["training_method", "learning_rate", "batch_size", "epochs"]:
            val1 = config1.get("training_config", {}).get(key)
            val2 = config2.get("training_config", {}).get(key)
            if val1 != val2:
                changes[key] = {"v1": val1, "v2": val2}
        
        return {"available": True, "changes": changes}
    
    async def _export_huggingface_format(self, src_path: str, dst_path: Path) -> None:
        """HuggingFace 형식으로 내보내기"""
        # 필요한 파일들 복사
        required_files = [
            "config.json", "tokenizer.json", "tokenizer_config.json",
            "special_tokens_map.json", "vocab.json", "merges.txt"
        ]
        
        src = Path(src_path)
        for file_name in required_files:
            src_file = src / file_name
            if src_file.exists():
                shutil.copy2(src_file, dst_path / file_name)
        
        # 모델 파일 복사
        for pattern in ["*.bin", "*.safetensors"]:
            for model_file in src.glob(pattern):
                shutil.copy2(model_file, dst_path / model_file.name)
    
    async def _export_onnx_format(self, src_path: str, dst_path: Path) -> None:
        """ONNX 형식으로 내보내기"""
        # ONNX 변환은 별도 구현 필요
        raise NotImplementedError("ONNX export not yet implemented")
    
    async def _export_archive_format(self, src_path: str, dst_path: Path) -> None:
        """압축 파일로 내보내기"""
        import zipfile
        
        archive_path = dst_path.parent / f"{dst_path.name}.zip"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            src = Path(src_path)
            for file_path in src.rglob('*'):
                if file_path.is_file():
                    arc_name = file_path.relative_to(src.parent)
                    zf.write(file_path, arc_name)


# 싱글톤 인스턴스
model_versioning_service = ModelVersioningService()