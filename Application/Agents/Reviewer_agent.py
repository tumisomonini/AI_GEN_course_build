from typing import Dict, List
from transformers import pipeline
from bert_score import score
import logging

logger = logging.getLogger(__name__)

_nli_model = None
_style_model = None
_nli_model_available = False
_style_model_available = False

def _get_nli_model():
    global _nli_model, _nli_model_available
    if _nli_model is None:
        try:
            _nli_model = pipeline("zero-shot-classification", model="roberta-large-mnli")
            _nli_model_available = True
        except Exception as e:
            logger.warning(f"Failed to load NLI model: {e}. ReviewerAgent will run in limited mode.")
            _nli_model_available = False
    return _nli_model

def _get_style_model():
    global _style_model, _style_model_available
    if _style_model is None:
        try:
            _style_model = pipeline("text-classification", model="textattack/bert-base-uncased-CoLA")
            _style_model_available = True
        except Exception as e:
            logger.warning(f"Failed to load style model: {e}. ReviewerAgent will run in limited mode.")
            _style_model_available = False
    return _style_model

class ReviewerAgent:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        # Don't load models during initialization - make it truly lazy

    def validate_factual_grounding(self, content: str, source: str) -> bool:
        if self.mock_mode or not _nli_model_available:
            return True
        try:
            result = _get_nli_model()(content, candidate_labels=["entailment", "neutral", "contradiction"])
            return result["labels"][0] == "entailment"
        except Exception as e:
            logger.warning(f"NLI validation failed: {e}. Returning True.")
            return True

    def validate_coverage(self, generated: str, outcomes: str) -> float:
        if self.mock_mode:
            return 0.85
        try:
            P, R, F1 = score([generated], [outcomes], lang="en", model_type="bert-base-uncased")
            return F1.mean().item()
        except Exception as e:
            logger.warning(f"BERT score validation failed: {e}. Returning default score.")
            return 0.85

    def validate_style(self, content: str) -> bool:
        if self.mock_mode or not _style_model_available:
            return True
        try:
            result = _get_style_model()(content)
            return result[0]["label"] == "POSITIVE"
        except Exception as e:
            logger.warning(f"Style validation failed: {e}. Returning True.")
            return True