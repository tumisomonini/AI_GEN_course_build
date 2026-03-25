from typing import Dict, List
from transformers import pipeline
from bert_score import score

class ReviewerAgent:
    def __init__(self):
        self.nli_model = pipeline("text-classification", model="roberta-large-mnli")
        self.style_model = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")

    def validate_factual_grounding(self, content: str, source: str) -> bool:
        result = self.nli_model(content, source, candidate_labels=["entailment", "neutral", "contradiction"])
        return result["labels"][0] == "entailment"

    def validate_coverage(self, generated: str, outcomes: str) -> float:
        P, R, F1 = score([generated], [outcomes], lang="en", model_type="bert-base-uncased")
        return F1.mean().item()

    def validate_style(self, content: str) -> bool:
        result = self.style_model(content)
        return result[0]["label"] == "POSITIVE"