from transformers_interpret import SequenceClassificationExplainer

from app.services.classifier import classifier_service


def explain_prediction(text: str, predicted_label: int) -> list[dict] | None:
    try:
        if not classifier_service.model or not classifier_service.tokenizer:
            print("Error: Model or tokenizer not loaded")
            return None

        explainer = SequenceClassificationExplainer(
            classifier_service.model,
            classifier_service.tokenizer,
        )
        # Use 'index' parameter instead of 'class_index' for newer transformers_interpret API
        attributions = explainer(text, index=predicted_label)
        return [{"token": token, "score": round(score, 4)} for token, score in attributions]
    except Exception as e:
        print(f"Error in explain_prediction: {e}")
        return None
