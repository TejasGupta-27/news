from transformers_interpret import SequenceClassificationExplainer

from app.services.classifier import classifier_service


def explain_prediction(text: str, predicted_label: int) -> list[dict]:
    explainer = SequenceClassificationExplainer(
        classifier_service.model,
        classifier_service.tokenizer,
    )
    attributions = explainer(text, class_index=predicted_label)
    return [{"token": token, "score": round(score, 4)} for token, score in attributions]
