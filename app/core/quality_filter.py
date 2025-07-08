"""
Quality filtering system for generated datasets
"""

import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import langdetect
from transformers import pipeline
import torch

from app.core.logging import logger
from app.core.config import settings


class QualityFilter:
    """Filter and score generated dataset samples based on quality metrics"""
    
    def __init__(self, language: str = "en"):
        self.language = language
        self.min_length = settings.MIN_SAMPLE_LENGTH if hasattr(settings, 'MIN_SAMPLE_LENGTH') else 10
        self.max_length = settings.MAX_SAMPLE_LENGTH if hasattr(settings, 'MAX_SAMPLE_LENGTH') else 2048
        
        # Download required NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            self.stop_words = set(stopwords.words('english' if language == "en" else language))
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}")
            self.stop_words = set()
        
        # Initialize toxicity classifier if available
        self.toxicity_classifier = None
        try:
            if torch.cuda.is_available():
                self.toxicity_classifier = pipeline(
                    "text-classification",
                    model="unitary/toxic-bert",
                    device=0
                )
            else:
                self.toxicity_classifier = pipeline(
                    "text-classification",
                    model="unitary/toxic-bert"
                )
        except Exception as e:
            logger.warning(f"Failed to load toxicity classifier: {e}")
    
    def filter_samples(
        self,
        samples: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter samples based on quality criteria
        
        Args:
            samples: List of generated samples
            config: Filtering configuration
        
        Returns:
            Tuple of (filtered_samples, statistics)
        """
        if not config:
            config = self._get_default_config()
        
        logger.info(f"Starting quality filtering for {len(samples)} samples")
        
        # Stage 1: Remove duplicates
        unique_samples = self._remove_duplicates(samples, config.get("duplicate_threshold", 0.95))
        logger.info(f"After duplicate removal: {len(unique_samples)} samples")
        
        # Stage 2: Length filtering
        length_filtered = self._filter_by_length(
            unique_samples,
            config.get("min_length", self.min_length),
            config.get("max_length", self.max_length)
        )
        logger.info(f"After length filtering: {len(length_filtered)} samples")
        
        # Stage 3: Language detection
        if config.get("check_language", True):
            language_filtered = self._filter_by_language(
                length_filtered,
                config.get("target_language", self.language)
            )
            logger.info(f"After language filtering: {len(language_filtered)} samples")
        else:
            language_filtered = length_filtered
        
        # Stage 4: Calculate quality scores
        scored_samples = self._calculate_quality_scores(language_filtered)
        
        # Stage 5: Filter by quality threshold
        quality_threshold = config.get("quality_threshold", 0.6)
        filtered_samples = [
            s for s in scored_samples
            if s.get("quality_score", 0) >= quality_threshold
        ]
        logger.info(f"After quality filtering: {len(filtered_samples)} samples")
        
        # Stage 6: Toxicity filtering
        if config.get("filter_toxic", True) and self.toxicity_classifier:
            filtered_samples = self._filter_toxic_content(
                filtered_samples,
                config.get("toxicity_threshold", 0.8)
            )
            logger.info(f"After toxicity filtering: {len(filtered_samples)} samples")
        
        # Stage 7: Domain relevance filtering
        if config.get("domain_keywords"):
            filtered_samples = self._filter_by_domain_relevance(
                filtered_samples,
                config.get("domain_keywords", []),
                config.get("domain_threshold", 0.3)
            )
            logger.info(f"After domain filtering: {len(filtered_samples)} samples")
        
        # Calculate statistics
        statistics = self._calculate_statistics(samples, filtered_samples)
        
        return filtered_samples, statistics
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default filtering configuration"""
        return {
            "duplicate_threshold": 0.95,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "check_language": True,
            "target_language": self.language,
            "quality_threshold": 0.6,
            "filter_toxic": True,
            "toxicity_threshold": 0.8,
            "domain_keywords": [],
            "domain_threshold": 0.3
        }
    
    def _remove_duplicates(
        self,
        samples: List[Dict[str, Any]],
        threshold: float = 0.95
    ) -> List[Dict[str, Any]]:
        """Remove duplicate or near-duplicate samples"""
        if not samples:
            return []
        
        # Extract text content
        texts = []
        for sample in samples:
            if "instruction" in sample and "output" in sample:
                text = f"{sample['instruction']} {sample['output']}"
            elif "response" in sample:
                text = sample["response"]
            else:
                text = str(sample)
            texts.append(text)
        
        # Use hash for exact duplicates
        seen_hashes = set()
        unique_indices = []
        
        for i, text in enumerate(texts):
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash not in seen_hashes:
                seen_hashes.add(text_hash)
                unique_indices.append(i)
        
        # Check for near-duplicates using TF-IDF
        if len(unique_indices) > 1 and threshold < 1.0:
            unique_texts = [texts[i] for i in unique_indices]
            
            try:
                vectorizer = TfidfVectorizer(max_features=1000)
                tfidf_matrix = vectorizer.fit_transform(unique_texts)
                
                # Calculate pairwise similarities
                similarities = cosine_similarity(tfidf_matrix)
                
                # Mark samples to keep
                keep_indices = []
                marked = set()
                
                for i in range(len(unique_indices)):
                    if i in marked:
                        continue
                    
                    keep_indices.append(unique_indices[i])
                    
                    # Mark similar samples
                    for j in range(i + 1, len(unique_indices)):
                        if similarities[i, j] > threshold:
                            marked.add(j)
                
                unique_indices = keep_indices
            except Exception as e:
                logger.warning(f"Near-duplicate detection failed: {e}")
        
        return [samples[i] for i in unique_indices]
    
    def _filter_by_length(
        self,
        samples: List[Dict[str, Any]],
        min_length: int,
        max_length: int
    ) -> List[Dict[str, Any]]:
        """Filter samples by text length"""
        filtered = []
        
        for sample in samples:
            # Extract text content
            if "instruction" in sample and "output" in sample:
                text = f"{sample['instruction']} {sample['output']}"
            elif "response" in sample:
                text = sample["response"]
            else:
                text = str(sample)
            
            # Count tokens (approximate)
            token_count = len(text.split())
            
            if min_length <= token_count <= max_length:
                filtered.append(sample)
        
        return filtered
    
    def _filter_by_language(
        self,
        samples: List[Dict[str, Any]],
        target_language: str
    ) -> List[Dict[str, Any]]:
        """Filter samples by detected language"""
        filtered = []
        
        for sample in samples:
            try:
                # Extract text content
                if "instruction" in sample and "output" in sample:
                    text = f"{sample['instruction']} {sample['output']}"
                elif "response" in sample:
                    text = sample["response"]
                else:
                    text = str(sample)
                
                # Detect language
                detected_lang = langdetect.detect(text)
                
                if detected_lang == target_language:
                    filtered.append(sample)
                    
            except Exception as e:
                # If language detection fails, include the sample
                logger.debug(f"Language detection failed: {e}")
                filtered.append(sample)
        
        return filtered
    
    def _calculate_quality_scores(
        self,
        samples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate quality scores for each sample"""
        scored_samples = []
        
        for sample in samples:
            # Extract text content
            if "instruction" in sample and "output" in sample:
                instruction = sample.get("instruction", "")
                output = sample.get("output", "")
                text = f"{instruction} {output}"
            elif "response" in sample:
                instruction = sample.get("prompt", "")
                output = sample.get("response", "")
                text = output
            else:
                instruction = ""
                output = str(sample)
                text = output
            
            # Calculate various quality metrics
            scores = {}
            
            # 1. Length score (prefer medium-length responses)
            tokens = text.split()
            token_count = len(tokens)
            if token_count < 20:
                scores["length"] = 0.5
            elif token_count < 50:
                scores["length"] = 0.7
            elif token_count < 200:
                scores["length"] = 1.0
            elif token_count < 500:
                scores["length"] = 0.8
            else:
                scores["length"] = 0.6
            
            # 2. Diversity score (vocabulary richness)
            unique_tokens = set(tokens)
            scores["diversity"] = min(len(unique_tokens) / max(token_count, 1), 1.0)
            
            # 3. Coherence score (based on sentence structure)
            try:
                sentences = sent_tokenize(text)
                if len(sentences) > 0:
                    avg_sentence_length = token_count / len(sentences)
                    if 10 <= avg_sentence_length <= 25:
                        scores["coherence"] = 1.0
                    elif 5 <= avg_sentence_length <= 35:
                        scores["coherence"] = 0.8
                    else:
                        scores["coherence"] = 0.6
                else:
                    scores["coherence"] = 0.5
            except:
                scores["coherence"] = 0.7
            
            # 4. Formatting score (check for proper formatting)
            scores["formatting"] = 1.0
            if text.count("```") % 2 != 0:  # Unclosed code blocks
                scores["formatting"] *= 0.8
            if text.count("**") % 2 != 0:  # Unclosed bold
                scores["formatting"] *= 0.9
            if text.count("*") % 2 != 0 and text.count("**") % 2 == 0:  # Unclosed italic
                scores["formatting"] *= 0.9
            
            # 5. Completeness score (for instruction-following)
            if instruction:
                # Check if output addresses the instruction
                instruction_words = set(word_tokenize(instruction.lower()))
                output_words = set(word_tokenize(output.lower()))
                overlap = instruction_words & output_words
                scores["completeness"] = min(len(overlap) / max(len(instruction_words), 1), 1.0)
            else:
                scores["completeness"] = 1.0
            
            # Calculate overall quality score
            weights = {
                "length": 0.2,
                "diversity": 0.2,
                "coherence": 0.25,
                "formatting": 0.15,
                "completeness": 0.2
            }
            
            quality_score = sum(scores[metric] * weights[metric] for metric in scores)
            
            # Add scores to sample
            sample_copy = sample.copy()
            sample_copy["quality_scores"] = scores
            sample_copy["quality_score"] = quality_score
            
            scored_samples.append(sample_copy)
        
        return scored_samples
    
    def _filter_toxic_content(
        self,
        samples: List[Dict[str, Any]],
        threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Filter out toxic or harmful content"""
        if not self.toxicity_classifier:
            return samples
        
        filtered = []
        
        for sample in samples:
            try:
                # Extract text content
                if "instruction" in sample and "output" in sample:
                    text = f"{sample['instruction']} {sample['output']}"
                elif "response" in sample:
                    text = sample["response"]
                else:
                    text = str(sample)
                
                # Check toxicity
                results = self.toxicity_classifier(text[:512])  # Limit length for efficiency
                
                # Get toxicity score
                toxic_score = 0
                for result in results:
                    if result["label"] == "TOXIC":
                        toxic_score = result["score"]
                        break
                
                # Keep sample if below threshold
                if toxic_score < threshold:
                    sample["toxicity_score"] = toxic_score
                    filtered.append(sample)
                    
            except Exception as e:
                logger.debug(f"Toxicity check failed: {e}")
                # If check fails, include the sample
                filtered.append(sample)
        
        return filtered
    
    def _filter_by_domain_relevance(
        self,
        samples: List[Dict[str, Any]],
        domain_keywords: List[str],
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Filter samples by domain relevance"""
        if not domain_keywords:
            return samples
        
        filtered = []
        domain_keywords_lower = [kw.lower() for kw in domain_keywords]
        
        for sample in samples:
            # Extract text content
            if "instruction" in sample and "output" in sample:
                text = f"{sample['instruction']} {sample['output']}"
            elif "response" in sample:
                text = sample["response"]
            else:
                text = str(sample)
            
            # Calculate domain relevance score
            text_lower = text.lower()
            words = word_tokenize(text_lower)
            
            keyword_count = sum(1 for word in words if word in domain_keywords_lower)
            relevance_score = keyword_count / max(len(words), 1)
            
            if relevance_score >= threshold:
                sample["domain_relevance_score"] = relevance_score
                filtered.append(sample)
        
        return filtered
    
    def _calculate_statistics(
        self,
        original_samples: List[Dict[str, Any]],
        filtered_samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate filtering statistics"""
        stats = {
            "original_count": len(original_samples),
            "filtered_count": len(filtered_samples),
            "filter_rate": 1 - (len(filtered_samples) / max(len(original_samples), 1)),
            "quality_scores": {}
        }
        
        if filtered_samples:
            # Calculate average quality scores
            quality_metrics = ["length", "diversity", "coherence", "formatting", "completeness"]
            
            for metric in quality_metrics:
                scores = [
                    s.get("quality_scores", {}).get(metric, 0)
                    for s in filtered_samples
                    if "quality_scores" in s
                ]
                if scores:
                    stats["quality_scores"][f"avg_{metric}"] = np.mean(scores)
                    stats["quality_scores"][f"std_{metric}"] = np.std(scores)
            
            # Overall quality score
            overall_scores = [s.get("quality_score", 0) for s in filtered_samples]
            if overall_scores:
                stats["quality_scores"]["avg_overall"] = np.mean(overall_scores)
                stats["quality_scores"]["std_overall"] = np.std(overall_scores)
                stats["quality_scores"]["min_overall"] = np.min(overall_scores)
                stats["quality_scores"]["max_overall"] = np.max(overall_scores)
        
        return stats


# Global instance
quality_filter = QualityFilter()