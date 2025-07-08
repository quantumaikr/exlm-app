"""Data preprocessing service for various dataset formats."""
from typing import List, Dict, Any, Optional, Tuple
import json
import csv
import io
import re
from pathlib import Path
import pandas as pd
import numpy as np
from transformers import AutoTokenizer
from datasets import Dataset, DatasetDict
import tiktoken
from langdetect import detect
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib

from app.core.config import settings
from app.schemas.dataset import DatasetFormat, PreprocessingConfig


class DataPreprocessingService:
    """Service for preprocessing and transforming datasets."""
    
    def __init__(self):
        self.tokenizers = {}
        self.openai_tokenizer = tiktoken.get_encoding("cl100k_base")
        
    def get_tokenizer(self, model_name: str):
        """Get or cache tokenizer for a specific model."""
        if model_name not in self.tokenizers:
            try:
                self.tokenizers[model_name] = AutoTokenizer.from_pretrained(model_name)
            except:
                # Fallback to a default tokenizer
                self.tokenizers[model_name] = AutoTokenizer.from_pretrained("bert-base-uncased")
        return self.tokenizers[model_name]
    
    async def preprocess_dataset(
        self,
        file_path: str,
        format: DatasetFormat,
        config: PreprocessingConfig,
        model_name: Optional[str] = None
    ) -> Tuple[Dataset, Dict[str, Any]]:
        """Preprocess dataset based on format and configuration."""
        # Load dataset
        raw_data = await self._load_dataset(file_path, format)
        
        # Apply preprocessing steps
        processed_data = []
        stats = {
            "total_samples": len(raw_data),
            "removed_samples": 0,
            "avg_input_length": 0,
            "avg_output_length": 0,
            "language_distribution": {},
            "quality_distribution": {}
        }
        
        tokenizer = self.get_tokenizer(model_name) if model_name else self.openai_tokenizer
        
        for idx, sample in enumerate(raw_data):
            # Skip if essential fields are missing
            if not self._validate_sample(sample, config):
                stats["removed_samples"] += 1
                continue
            
            # Clean text
            if config.clean_text:
                sample = self._clean_text_fields(sample)
            
            # Remove duplicates (simple hash-based)
            if config.remove_duplicates:
                sample_hash = self._get_sample_hash(sample)
                if hasattr(self, '_seen_hashes') and sample_hash in self._seen_hashes:
                    stats["removed_samples"] += 1
                    continue
                if not hasattr(self, '_seen_hashes'):
                    self._seen_hashes = set()
                self._seen_hashes.add(sample_hash)
            
            # Filter by length
            if config.min_length or config.max_length:
                text_length = self._calculate_text_length(sample, tokenizer)
                if config.min_length and text_length < config.min_length:
                    stats["removed_samples"] += 1
                    continue
                if config.max_length and text_length > config.max_length:
                    stats["removed_samples"] += 1
                    continue
            
            # Detect language
            if config.filter_languages:
                detected_lang = self._detect_language(sample)
                if detected_lang not in config.filter_languages:
                    stats["removed_samples"] += 1
                    continue
                stats["language_distribution"][detected_lang] = \
                    stats["language_distribution"].get(detected_lang, 0) + 1
            
            # Add metadata
            if config.add_metadata:
                sample["metadata"] = {
                    "index": idx,
                    "source_file": Path(file_path).name,
                    "preprocessing_version": "1.0"
                }
            
            processed_data.append(sample)
        
        # Convert to specific format if needed
        if config.target_format and config.target_format != format:
            processed_data = self._convert_format(processed_data, format, config.target_format)
        
        # Calculate final statistics
        if processed_data:
            stats["avg_input_length"] = np.mean([
                self._calculate_text_length(s, tokenizer, field="input") 
                for s in processed_data[:1000]  # Sample for efficiency
            ])
            stats["avg_output_length"] = np.mean([
                self._calculate_text_length(s, tokenizer, field="output") 
                for s in processed_data[:1000]
            ])
        
        # Create HuggingFace Dataset
        dataset = Dataset.from_list(processed_data)
        
        # Apply train/test split if configured
        if config.train_test_split:
            dataset = dataset.train_test_split(
                test_size=config.test_split_ratio,
                seed=42
            )
        
        return dataset, stats
    
    async def _load_dataset(self, file_path: str, format: DatasetFormat) -> List[Dict[str, Any]]:
        """Load dataset from file based on format."""
        data = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if format == DatasetFormat.JSONL:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
            
            elif format == DatasetFormat.JSON:
                json_data = json.load(f)
                if isinstance(json_data, list):
                    data = json_data
                else:
                    data = [json_data]
            
            elif format == DatasetFormat.CSV:
                reader = csv.DictReader(f)
                data = list(reader)
            
            elif format == DatasetFormat.TSV:
                reader = csv.DictReader(f, delimiter='\t')
                data = list(reader)
            
            elif format == DatasetFormat.PARQUET:
                df = pd.read_parquet(file_path)
                data = df.to_dict('records')
            
            elif format == DatasetFormat.ALPACA:
                # Alpaca format: instruction, input, output
                json_data = json.load(f)
                for item in json_data:
                    data.append({
                        "instruction": item.get("instruction", ""),
                        "input": item.get("input", ""),
                        "output": item.get("output", "")
                    })
            
            elif format == DatasetFormat.SHAREGPT:
                # ShareGPT format: conversations with from/value pairs
                json_data = json.load(f)
                for item in json_data:
                    if "conversations" in item:
                        data.append(item)
        
        return data
    
    def _validate_sample(self, sample: Dict[str, Any], config: PreprocessingConfig) -> bool:
        """Validate if sample has required fields."""
        required_fields = config.required_fields or ["input", "output"]
        for field in required_fields:
            if field not in sample or not sample[field]:
                return False
        return True
    
    def _clean_text_fields(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """Clean text fields in the sample."""
        cleaned = sample.copy()
        
        for key, value in cleaned.items():
            if isinstance(value, str):
                # Remove excessive whitespace
                value = re.sub(r'\s+', ' ', value)
                # Remove control characters
                value = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', value)
                # Trim
                value = value.strip()
                cleaned[key] = value
        
        return cleaned
    
    def _get_sample_hash(self, sample: Dict[str, Any]) -> str:
        """Generate hash for duplicate detection."""
        # Use main content fields for hashing
        content = ""
        for field in ["instruction", "input", "output", "text", "prompt", "response"]:
            if field in sample:
                content += str(sample[field])
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def _calculate_text_length(
        self, 
        sample: Dict[str, Any], 
        tokenizer: Any,
        field: Optional[str] = None
    ) -> int:
        """Calculate token length of text."""
        if field:
            text = sample.get(field, "")
        else:
            # Combine all text fields
            text = " ".join([
                str(v) for v in sample.values() 
                if isinstance(v, str)
            ])
        
        if hasattr(tokenizer, 'encode'):
            # HuggingFace tokenizer
            return len(tokenizer.encode(text))
        else:
            # Tiktoken
            return len(tokenizer.encode(text))
    
    def _detect_language(self, sample: Dict[str, Any]) -> str:
        """Detect language of the sample."""
        # Combine text fields
        text = " ".join([
            str(v) for v in sample.values() 
            if isinstance(v, str)
        ])[:500]  # Use first 500 chars for efficiency
        
        try:
            return detect(text)
        except:
            return "unknown"
    
    def _convert_format(
        self, 
        data: List[Dict[str, Any]], 
        source_format: DatasetFormat,
        target_format: DatasetFormat
    ) -> List[Dict[str, Any]]:
        """Convert between dataset formats."""
        converted = []
        
        for sample in data:
            if target_format == DatasetFormat.ALPACA:
                # Convert to Alpaca format
                converted_sample = {
                    "instruction": sample.get("instruction", sample.get("prompt", "")),
                    "input": sample.get("input", ""),
                    "output": sample.get("output", sample.get("response", ""))
                }
            
            elif target_format == DatasetFormat.SHAREGPT:
                # Convert to ShareGPT format
                conversations = []
                if "instruction" in sample or "prompt" in sample:
                    conversations.append({
                        "from": "human",
                        "value": sample.get("instruction", sample.get("prompt", ""))
                    })
                if "output" in sample or "response" in sample:
                    conversations.append({
                        "from": "gpt",
                        "value": sample.get("output", sample.get("response", ""))
                    })
                converted_sample = {"conversations": conversations}
            
            else:
                # Default: keep as is
                converted_sample = sample
            
            converted.append(converted_sample)
        
        return converted
    
    async def analyze_dataset_quality(
        self,
        dataset: Dataset,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze dataset quality metrics."""
        quality_report = {
            "total_samples": len(dataset),
            "field_coverage": {},
            "length_statistics": {},
            "diversity_metrics": {},
            "quality_issues": []
        }
        
        # Field coverage analysis
        all_fields = set()
        for sample in dataset:
            all_fields.update(sample.keys())
        
        for field in all_fields:
            coverage = sum(1 for s in dataset if field in s and s[field])
            quality_report["field_coverage"][field] = {
                "count": coverage,
                "percentage": (coverage / len(dataset)) * 100
            }
        
        # Length statistics
        text_lengths = []
        for sample in dataset[:1000]:  # Sample for efficiency
            text = " ".join([str(v) for v in sample.values() if isinstance(v, str)])
            text_lengths.append(len(text.split()))
        
        quality_report["length_statistics"] = {
            "mean": np.mean(text_lengths),
            "median": np.median(text_lengths),
            "std": np.std(text_lengths),
            "min": np.min(text_lengths),
            "max": np.max(text_lengths)
        }
        
        # Diversity metrics (using TF-IDF)
        if len(dataset) > 100:
            sample_texts = [
                " ".join([str(v) for v in s.values() if isinstance(v, str)])
                for s in dataset[:500]
            ]
            
            vectorizer = TfidfVectorizer(max_features=1000)
            tfidf_matrix = vectorizer.fit_transform(sample_texts)
            
            # Calculate average pairwise similarity
            similarities = []
            for i in range(min(100, len(sample_texts))):
                for j in range(i + 1, min(100, len(sample_texts))):
                    sim = cosine_similarity(tfidf_matrix[i], tfidf_matrix[j])[0][0]
                    similarities.append(sim)
            
            quality_report["diversity_metrics"] = {
                "avg_similarity": np.mean(similarities),
                "vocabulary_size": len(vectorizer.vocabulary_)
            }
        
        # Identify quality issues
        if quality_report["length_statistics"]["min"] < 10:
            quality_report["quality_issues"].append({
                "type": "short_samples",
                "severity": "medium",
                "description": "Some samples are very short (< 10 words)"
            })
        
        if quality_report["diversity_metrics"].get("avg_similarity", 0) > 0.8:
            quality_report["quality_issues"].append({
                "type": "low_diversity",
                "severity": "high",
                "description": "Dataset has low diversity (high similarity between samples)"
            })
        
        return quality_report
    
    def clean_for_training(self, dataset: Dataset, model_name: str) -> Dataset:
        """Final cleaning for model training."""
        tokenizer = self.get_tokenizer(model_name)
        
        def process_sample(sample):
            # Ensure all text fields are strings
            for key in sample:
                if sample[key] is None:
                    sample[key] = ""
                elif not isinstance(sample[key], str):
                    sample[key] = str(sample[key])
            return sample
        
        return dataset.map(process_sample)


# Create singleton instance
data_preprocessing_service = DataPreprocessingService()