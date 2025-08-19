import replicate
import logging
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseCompute, ExecuteResponse, GetResponse
from settings import get_settings
from domain.entities import GrantFile
from utils.json_mode import create_json_mode_handler, ResponseFormatConfig, ResponseFormat

logger = logging.getLogger(__name__)



@dataclass
class ReplicateInput:
    """Data class for Replicate API input structure."""
    prompt: str

@dataclass
class ReplicateRequest:
    """Data class for Replicate API request structure."""
    model: str
    input: ReplicateInput

@dataclass
class ReplicateUrls:
    """Data class for Replicate API URLs."""
    cancel: str
    get: str
    web: str

@dataclass
class ReplicatePredictionResponse:
    """Data class for Replicate API prediction response."""
    id: str
    model: str
    version: str
    input: Dict[str, Any]
    logs: str = ""
    output: Any = None
    data_removed: bool = False
    error: str = None
    status: str = "starting"
    created_at: str = None
    started_at: str = None
    completed_at: str = None
    urls: ReplicateUrls = None

PROMPT_DATA_SEPARATOR = "-----" * 80 + "\n"

# According to doc max context length for deepseek-v3 is 128K tokens.
# However, according to different sources, the actual usable limit is around 25k tokens
# https://www.reddit.com/r/SillyTavernAI/comments/1k88xkz/is_the_actual_context_size_for_deepseek_models/
# Using conservative estimate of 3 characters per token.
# This is a safe middle-ground, as the actual ratio can vary (from ~4 for simple English to less for multilingual text).
# In case different models are used, this value should be adjusted accordingly.
MAX_PROMPT_CHAR_LIMIT = 75000


class ReplicateLlmInference(BaseCompute):
    """Replicate API provider for ML model inference."""

    def __init__(self):
        self.settings = get_settings()
        self.client = replicate.Client(
            api_token=self.settings.replicate_api_token
        )
        self.model_name = "deepseek-ai/deepseek-v3"
        # Store response formats for predictions
        self._prediction_formats: Dict[str, Dict[str, Any]] = {}

    def execute(self, grant_file: GrantFile, files_content: list[str], response_format: Optional[Dict[str, Any]] = None) -> ExecuteResponse:
        # Create JSON mode handler if needed
        json_handler = create_json_mode_handler(response_format) if response_format else None
        
        # Build base prompt
        prompt = self._build_prompt(grant_file, files_content)
        
        # Modify prompt for JSON mode if needed
        if json_handler and response_format and response_format.get("type") == "json_object":
            prompt = json_handler.modify_prompt_for_json(prompt)
            logger.info("Modified prompt to enforce JSON output mode")
        
        try:
            # Create prediction with potentially modified prompt
            prediction = self.client.predictions.create(
                model=self.model_name,
                input={"prompt": prompt}
            )
            
            # Store response format for this prediction if provided
            if response_format:
                self._prediction_formats[prediction.id] = response_format
                logger.info(f"Stored response format for prediction {prediction.id}: {response_format}")
            
            return ExecuteResponse(
                id=prediction.id,
                created_at=prediction.created_at
            )
        except Exception as e:
            raise Exception(f"Failed to create prediction: {str(e)}")

    def get(self, prediction_id: str) -> GetResponse:
        try:
            prediction = self.client.predictions.get(prediction_id)
            started_at = prediction.started_at if prediction.started_at else None
            finished_at = prediction.completed_at if prediction.completed_at else None
            result = prediction.output if prediction.output else None

            # Convert list result to string if needed
            if isinstance(result, list):
                result = ''.join(result)

            # Check if this prediction has a stored response format
            response_format = self._prediction_formats.get(prediction_id)
            
            # Process result based on response format if completed
            if result is not None and response_format and prediction.status == "succeeded":
                json_handler = create_json_mode_handler(response_format)
                if response_format.get("type") == "json_object":
                    # Process JSON response
                    processed_result, error = json_handler.process_response(result)
                    
                    if isinstance(processed_result, dict):
                        # Successfully parsed JSON - convert back to string for storage
                        result = json.dumps(processed_result)
                        logger.info(f"Successfully processed JSON response for prediction {prediction_id}")
                    elif error:
                        # JSON parsing failed - log error but return original result
                        logger.error(f"Failed to parse JSON response for prediction {prediction_id}: {error}")
                        # Note: In a production system, you might want to handle this differently
                        # For now, we'll return the original response with a wrapper indicating the error
                        error_wrapper = {
                            "error": "json_parse_failed",
                            "error_message": error,
                            "raw_response": result[:1000] if len(result) > 1000 else result
                        }
                        result = json.dumps(error_wrapper)
                
            # Clean up stored format after terminal states
            if prediction.status in ["succeeded", "failed", "canceled"]:
                self._prediction_formats.pop(prediction_id, None)

            return GetResponse(
                id=prediction.id,
                status=prediction.status,
                started_at=started_at,
                finished_at=finished_at,
                result=result
            )
        except Exception as e:
            raise Exception(f"Failed to get prediction: {str(e)}")

    def cancel(self, prediction_id: str) -> bool:
        """Cancel a running prediction."""
        try:
            # Use the Replicate client directly
            prediction = self.client.predictions.cancel(prediction_id)
            return prediction.status == "canceled"
        except Exception:
            return False


    def _build_prompt(self, grant_file: GrantFile, files_content: list[str]):
        prompt_template = grant_file.parameters.get("prompt", "")
        concatenated_data = (
            "\n"
            + PROMPT_DATA_SEPARATOR.join(files_content)
            + "\n"
            + PROMPT_DATA_SEPARATOR
        )

        # Calculate available space for data to not exceed the model's context limit
        template_base_length = len(prompt_template.replace("{{data}}", ""))
        available_space_for_data = MAX_PROMPT_CHAR_LIMIT - template_base_length

        # Handle case where the prompt template itself is too long
        if available_space_for_data <= 0:
            logger.warning(
                f"Prompt template is too long ({template_base_length} chars), exceeding the limit of {MAX_PROMPT_CHAR_LIMIT}. "
                "No data will be included in the prompt."
            )
            concatenated_data = ""
        # Truncate the data if it's too large to fit in the available space
        elif len(concatenated_data) > available_space_for_data:
            truncation_message = f"\n\n--- DATA TRUNCATED TO FIT MODEL'S CONTEXT WINDOW ---"
            # Recalculate space considering the truncation message
            available_space_for_data -= len(truncation_message)

            if available_space_for_data > 0:
                concatenated_data = concatenated_data[:available_space_for_data] + truncation_message
                logger.warning(f"Input data was truncated to fit within the {MAX_PROMPT_CHAR_LIMIT} character limit.")
            else:
                # Not enough space for even a truncated message, send empty data
                concatenated_data = ""
                logger.warning("Prompt template is too long, no space for data or truncation message.")

        return prompt_template.replace("{{data}}", concatenated_data)

