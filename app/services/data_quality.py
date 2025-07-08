"""Data quality evaluation service."""
from typing import List, Dict, Any, Optional, Tuple
import re
import json
import numpy as np
from collections import Counter
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
import torch
import nltk
from langdetect import detect, LangDetectException
import tiktoken

from app.schemas.dataset import QualityMetrics, DataSampleBase
from app.core.config import settings


# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except:
    pass


class DataQualityService:
    """Service for evaluating data quality metrics."""
    
    def __init__(self):
        self.toxicity_classifier = None
        self.quality_classifier = None
        self.openai_tokenizer = tiktoken.get_encoding("cl100k_base")
        self._init_models()
    
    def _init_models(self):
        """Initialize ML models for quality evaluation."""
        try:
            # Initialize toxicity classifier
            self.toxicity_classifier = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                device=0 if torch.cuda.is_available() else -1
            )
        except:
            print("Warning: Could not load toxicity classifier")
        
        try:
            # Initialize quality classifier (placeholder - would use custom model)
            self.quality_classifier = None  # TODO: Load custom quality model
        except:
            print("Warning: Could not load quality classifier")
    
    async def evaluate_dataset_quality(
        self,
        samples: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None
    ) -> QualityMetrics:
        """Evaluate quality metrics for entire dataset."""
        if not samples:
            raise ValueError("No samples provided for evaluation")
        
        # Initialize metrics
        scores = {
            "completeness": [],
            "accuracy": [],
            "relevance": [],
            "consistency": [],
            "diversity": [],
            "toxicity": [],
            "length": [],
            "quality": []
        }
        
        # Sample for efficiency if dataset is large
        eval_samples = samples
        if len(samples) > 1000:
            import random
            eval_samples = random.sample(samples, 1000)
        
        # Evaluate each sample
        for sample in eval_samples:
            sample_metrics = await self.evaluate_sample_quality(sample)
            for key, value in sample_metrics.items():
                if key in scores:
                    scores[key].append(value)
        
        # Calculate diversity metrics
        diversity_score = self._calculate_diversity(eval_samples)
        
        # Calculate duplicate rate
        duplicate_rate = self._calculate_duplicate_rate(samples)
        
        # Calculate vocabulary size
        vocab_size = self._calculate_vocabulary_size(eval_samples)
        
        # Aggregate scores
        overall_scores = {
            "completeness": np.mean(scores["completeness"]) if scores["completeness"] else 0,
            "accuracy": np.mean(scores["accuracy"]) if scores["accuracy"] else 8.0,  # Default
            "relevance": np.mean(scores["relevance"]) if scores["relevance"] else 0,
            "consistency": np.mean(scores["consistency"]) if scores["consistency"] else 0,
            "diversity": diversity_score,
            "toxicity": np.mean(scores["toxicity"]) if scores["toxicity"] else 0
        }
        
        # Calculate overall score (weighted average)
        weights = {
            "completeness": 0.2,
            "accuracy": 0.2,
            "relevance": 0.25,
            "consistency": 0.15,
            "diversity": 0.2
        }
        
        overall_score = sum(
            overall_scores[metric] * weight 
            for metric, weight in weights.items()
        )
        
        # Count high/low quality samples
        quality_scores = scores["quality"] if scores["quality"] else [overall_score] * len(samples)
        high_quality_count = sum(1 for s in quality_scores if s >= 7.0)
        low_quality_count = sum(1 for s in quality_scores if s < 7.0)
        
        return QualityMetrics(
            overall_score=min(10.0, overall_score),
            completeness=overall_scores["completeness"],
            accuracy=overall_scores["accuracy"],
            relevance=overall_scores["relevance"],
            consistency=overall_scores["consistency"],
            diversity=overall_scores["diversity"],
            toxicity=overall_scores["toxicity"],
            total_samples=len(samples),
            high_quality_samples=high_quality_count,
            low_quality_samples=low_quality_count,
            average_length=np.mean(scores["length"]) if scores["length"] else 0,
            vocabulary_size=vocab_size,
            duplicate_rate=duplicate_rate
        )
    
    async def evaluate_sample_quality(
        self,
        sample: Dict[str, Any]
    ) -> Dict[str, float]:
        """Evaluate quality metrics for a single sample."""
        metrics = {}
        
        # Extract text content
        instruction = sample.get("instruction", sample.get("prompt", ""))
        response = sample.get("output", sample.get("response", sample.get("text", "")))
        
        # Completeness score
        metrics["completeness"] = self._evaluate_completeness(instruction, response)
        
        # Relevance score
        metrics["relevance"] = self._evaluate_relevance(instruction, response)
        
        # Consistency score
        metrics["consistency"] = self._evaluate_consistency(response)
        
        # Toxicity score
        metrics["toxicity"] = await self._evaluate_toxicity(response)
        
        # Length
        metrics["length"] = len(self.openai_tokenizer.encode(response))
        
        # Overall quality score
        metrics["quality"] = np.mean([
            metrics["completeness"],
            metrics["relevance"],
            metrics["consistency"],
            10.0 - (metrics["toxicity"] * 10)  # Invert toxicity
        ])
        
        return metrics
    
    def _evaluate_completeness(self, instruction: str, response: str) -> float:
        """Evaluate if response completely addresses the instruction."""
        if not instruction or not response:
            return 0.0
        
        # Check response length relative to instruction
        if len(response) < len(instruction) * 0.5:
            return 3.0
        
        # Check for common incomplete patterns
        incomplete_patterns = [
            r"I cannot",
            r"I don't have enough",
            r"I need more information",
            r"Could you provide",
            r"Please clarify"
        ]
        
        for pattern in incomplete_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return 5.0
        
        # Check for complete answer indicators
        complete_patterns = [
            r"In conclusion",
            r"To summarize",
            r"Here's",
            r"The answer is",
            r"[0-9]+\.",  # Numbered lists
            r"First.*Second.*Third"  # Sequential explanations
        ]
        
        completeness_score = 7.0
        for pattern in complete_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                completeness_score = min(10.0, completeness_score + 1.0)
        
        return completeness_score
    
    def _evaluate_relevance(self, instruction: str, response: str) -> float:
        """Evaluate relevance between instruction and response."""
        if not instruction or not response:
            return 0.0
        
        # Use TF-IDF similarity
        try:
            vectorizer = TfidfVectorizer(max_features=100)
            tfidf_matrix = vectorizer.fit_transform([instruction, response])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Convert similarity to 0-10 scale
            return min(10.0, similarity * 15)
        except:
            return 7.0  # Default moderate relevance
    
    def _evaluate_consistency(self, response: str) -> float:
        """Evaluate internal consistency of response."""
        if not response:
            return 0.0
        
        # Check for contradictions
        contradiction_patterns = [
            (r"yes", r"no"),
            (r"true", r"false"),
            (r"always", r"never"),
            (r"correct", r"incorrect"),
            (r"right", r"wrong")
        ]
        
        consistency_score = 9.0
        response_lower = response.lower()
        
        for pos_pattern, neg_pattern in contradiction_patterns:
            if re.search(pos_pattern, response_lower) and re.search(neg_pattern, response_lower):
                consistency_score -= 2.0
        
        # Check for repetition (reduces consistency)
        sentences = response.split('.')
        if len(sentences) > 3:
            unique_sentences = len(set(sentences))
            repetition_ratio = unique_sentences / len(sentences)
            if repetition_ratio < 0.8:
                consistency_score -= 2.0
        
        return max(0.0, consistency_score)
    
    async def _evaluate_toxicity(self, text: str) -> float:
        """Evaluate toxicity of text."""
        if not text or not self.toxicity_classifier:
            return 0.0
        
        try:
            # Truncate text for efficiency
            text_truncated = text[:512]
            
            results = self.toxicity_classifier(text_truncated)
            
            # Extract toxicity score
            for result in results:
                if result['label'] == 'TOXIC':
                    return result['score']
            
            return 0.0
        except:
            return 0.0
    
    def _calculate_diversity(self, samples: List[Dict[str, Any]]) -> float:
        """Calculate diversity score for dataset."""
        if len(samples) < 2:
            return 10.0
        
        # Extract text from samples
        texts = []
        for sample in samples[:500]:  # Limit for efficiency
            text = " ".join([
                str(sample.get(field, ""))
                for field in ["instruction", "output", "response", "text", "prompt"]
                if field in sample
            ])
            texts.append(text)
        
        if not texts:
            return 5.0
        
        # Calculate pairwise similarities
        try:
            vectorizer = TfidfVectorizer(max_features=500)
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            # Sample random pairs for efficiency
            num_comparisons = min(100, len(texts) * (len(texts) - 1) // 2)
            similarities = []
            
            import random
            for _ in range(num_comparisons):
                i, j = random.sample(range(len(texts)), 2)
                sim = cosine_similarity(tfidf_matrix[i:i+1], tfidf_matrix[j:j+1])[0][0]
                similarities.append(sim)
            
            # Convert average similarity to diversity score
            avg_similarity = np.mean(similarities)
            diversity_score = (1 - avg_similarity) * 10
            
            return min(10.0, max(0.0, diversity_score))
        except:
            return 7.0  # Default moderate diversity
    
    def _calculate_duplicate_rate(self, samples: List[Dict[str, Any]]) -> float:
        """Calculate percentage of duplicate samples."""
        if not samples:
            return 0.0
        
        # Create hashes for each sample
        hashes = []
        for sample in samples:
            # Combine main text fields
            text = " ".join([
                str(sample.get(field, ""))
                for field in ["instruction", "output", "response", "text", "prompt"]
                if field in sample
            ])
            
            # Create hash
            text_hash = hashlib.md5(text.encode()).hexdigest()
            hashes.append(text_hash)
        
        # Calculate duplicate rate
        unique_hashes = len(set(hashes))
        duplicate_count = len(hashes) - unique_hashes
        
        return (duplicate_count / len(hashes)) * 100
    
    def _calculate_vocabulary_size(self, samples: List[Dict[str, Any]]) -> int:
        """Calculate vocabulary size across samples."""
        vocabulary = set()
        
        for sample in samples[:1000]:  # Limit for efficiency
            text = " ".join([
                str(sample.get(field, ""))
                for field in ["instruction", "output", "response", "text", "prompt"]
                if field in sample
            ])
            
            # Simple tokenization
            words = re.findall(r'\b\w+\b', text.lower())
            vocabulary.update(words)
        
        return len(vocabulary)
    
    async def identify_quality_issues(
        self,
        samples: List[Dict[str, Any]],
        metrics: QualityMetrics
    ) -> List[Dict[str, Any]]:
        """Identify specific quality issues in dataset."""
        issues = []
        
        # Check for high duplicate rate
        if metrics.duplicate_rate > 5.0:
            issues.append({
                "type": "duplicate",
                "severity": "high" if metrics.duplicate_rate > 10.0 else "medium",
                "count": int(len(samples) * metrics.duplicate_rate / 100),
                "description": f"Dataset contains {metrics.duplicate_rate:.1f}% duplicate samples"
            })
        
        # Check for short responses
        short_samples = 0
        for sample in samples[:1000]:
            response = sample.get("output", sample.get("response", ""))
            if len(response.split()) < 10:
                short_samples += 1
        
        if short_samples > 100:
            issues.append({
                "type": "short",
                "severity": "medium",
                "count": short_samples,
                "description": "Many responses are too short (< 10 words)"
            })
        
        # Check for toxicity
        if metrics.toxicity > 0.1:
            issues.append({
                "type": "toxic",
                "severity": "high",
                "count": int(len(samples) * metrics.toxicity),
                "description": f"Dataset contains toxic content ({metrics.toxicity:.1%} of samples)"
            })
        
        # Check for low diversity
        if metrics.diversity < 5.0:
            issues.append({
                "type": "low_diversity",
                "severity": "medium",
                "count": len(samples),
                "description": "Dataset has low diversity (many similar samples)"
            })
        
        # Check for poor relevance
        if metrics.relevance < 6.0:
            issues.append({
                "type": "irrelevant",
                "severity": "medium",
                "count": int(len(samples) * (10 - metrics.relevance) / 10),
                "description": "Many responses are not relevant to instructions"
            })
        
        return issues


# Create singleton instance
data_quality_service = DataQualityService()