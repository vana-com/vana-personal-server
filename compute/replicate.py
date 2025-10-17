import replicate
import logging
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseCompute, ExecuteResponse, GetResponse
from settings import get_settings
from domain.entities import GrantFile
from domain.operation_context import OperationContext
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
    """
    Replicate API provider for LLM inference operations.
    
    Handles end-to-end LLM inference including prompt construction, data injection,
    JSON mode enforcement, and asynchronous prediction lifecycle management.
    Uses DeepSeek-V3 model by default with configurable parameters.
    
    Attributes:
        client: Authenticated Replicate API client
        model_name: Target model identifier (default: deepseek-ai/deepseek-v3)
        _prediction_formats: Cache mapping prediction IDs to response format configs
        
    Configuration:
        MAX_PROMPT_CHAR_LIMIT: Maximum prompt size (75,000 chars ~25k tokens)
        PROMPT_DATA_SEPARATOR: Delimiter between data files ("-----" x 80)
        
    Note:
        Token limits are conservative estimates (3 chars/token) to ensure
        prompts fit within model context windows across different languages.
    """

    def __init__(self):
        """
        Initialize Replicate client with API credentials.
        
        Raises:
            ValueError: If REPLICATE_API_TOKEN is not configured
        """
        self.settings = get_settings()
        self.client = replicate.Client(
            api_token=self.settings.replicate_api_token
        )
        self.model_name = "deepseek-ai/deepseek-v3"
        # Store response formats for predictions
        self._prediction_formats: Dict[str, Dict[str, Any]] = {}

    async def execute(self, grant_file: GrantFile, files_content: list[str], context: OperationContext) -> ExecuteResponse:
        """
        Execute LLM inference operation with user data.

        Creates a Replicate prediction with the provided prompt template and data.
        Handles JSON mode configuration if specified in grant file parameters.
        Automatically ensures data is included via {{data}} placeholder.

        Args:
            grant_file: Permission grant containing prompt template and parameters.
                Expected parameters:
                - prompt (str): Template with optional {{data}} placeholder
                - response_format (dict, optional): JSON mode configuration
            files_content: List of decrypted file contents to inject into prompt
            context: Operation context for execution (provided for consistency, not used by Replicate provider)

        Returns:
            ExecuteResponse with prediction ID and creation timestamp

        Raises:
            Exception: If prediction creation fails or Replicate API errors

        Note:
            Predictions are asynchronous. Use get() method to poll for results.
            Max tokens set to 16384 (configurable in future versions).
        """
        # Extract response_format from grant file parameters
        response_format = grant_file.parameters.get("response_format")

        # Create JSON mode handler if needed
        json_handler = create_json_mode_handler(response_format) if response_format else None

        # Build base prompt
        prompt = self._build_prompt(grant_file, files_content)

        # Modify prompt for JSON mode if needed
        if json_handler and response_format and response_format.get("type") == "json_object":
            prompt = json_handler.modify_prompt_for_json(prompt)
            logger.info("Modified prompt to enforce JSON output mode")

        try:
            # Log operation-to-prediction mapping for debugging/monitoring
            # This enables tracing personal server operations to Replicate dashboard
            logger.info(f"Creating Replicate prediction for operation_id={context.operation_id}")

            # Create prediction with potentially modified prompt
            prediction = self.client.predictions.create(
                model=self.model_name,
                input={
                    "prompt": prompt,
                    "max_tokens": 16384,  # Customize this value as needed (min: 2, max: 20480, default: 1024)
                    # "temperature": 0.6,  # Optional: uncomment if needed (default: 0.6)
                    # "presence_penalty": 0,  # Optional: uncomment if needed (default: 0)
                    # "frequency_penalty": 0,  # Optional: uncomment if needed (default: 0)
                    # "top_p": 1,  # Optional: uncomment if needed (default: 1)
                }
            )

            # Log the mapping for traceability (Replicate API doesn't support custom metadata)
            logger.info(
                f"Replicate prediction created: "
                f"operation_id={context.operation_id} -> prediction_id={prediction.id}"
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
        """
        Retrieve prediction status and results.
        
        Polls Replicate API for prediction status. Processes JSON responses
        if response_format was specified during creation. Cleans up cached
        formats after terminal states.
        
        Args:
            prediction_id: Unique prediction identifier from execute()
            
        Returns:
            GetResponse with status, timestamps, and result (if completed)
            
        Raises:
            Exception: If prediction retrieval fails
            
        Note:
            Results are converted from list to string if needed.
            JSON mode responses are validated and re-stringified.
            Failed JSON parsing returns error wrapper with raw response.
        """
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
                        # Successfully parsed JSON - use dict directly
                        result = processed_result
                        logger.info(f"Successfully processed JSON response for prediction {prediction_id}")
                    elif error:
                        # JSON parsing failed - log error but return original result
                        logger.error(f"Failed to parse JSON response for prediction {prediction_id}: {error}")
                        # Note: In a production system, you might want to handle this differently
                        # For now, we'll return the original response with a wrapper indicating the error
                        result = {
                            "error": "json_parse_failed",
                            "error_message": error,
                            "raw_response": result[:1000] if len(result) > 1000 else result
                        }

            # Clean up stored format after terminal states
            if prediction.status in ["succeeded", "failed", "canceled"]:
                self._prediction_formats.pop(prediction_id, None)

            # Convert result to dict format
            result_dict = None
            if result is not None:
                if isinstance(result, dict):
                    # Already a dict (either from JSON parsing above or native dict)
                    result_dict = result
                else:
                    # Wrap non-dict results (strings, etc.) in a dict
                    result_dict = {"output": result}
            
            return GetResponse(
                id=prediction.id,
                status=prediction.status,
                started_at=started_at,
                finished_at=finished_at,
                result=result_dict
            )
        except Exception as e:
            raise Exception(f"Failed to get prediction: {str(e)}")

    def cancel(self, prediction_id: str) -> bool:
        """
        Cancel a running prediction.
        
        Attempts best-effort cancellation of an in-progress prediction.
        Only affects predictions in 'starting' or 'processing' states.
        
        Args:
            prediction_id: Unique prediction identifier to cancel
            
        Returns:
            True if cancellation succeeded, False otherwise
            
        Note:
            Cancellation may not take effect if prediction is near completion.
            Always check status after cancellation attempt.
        """
        try:
            # Use the Replicate client directly
            prediction = self.client.predictions.cancel(prediction_id)
            return prediction.status == "canceled"
        except Exception:
            return False


    def _build_prompt(self, grant_file: GrantFile, files_content: list[str]) -> str:
        """
        Construct final prompt with data injection.
        
        Ensures data is always included by appending {{data}} placeholder
        if not present in template. Handles truncation when content exceeds
        model context limits.
        
        Args:
            grant_file: Permission grant with prompt template in parameters
            files_content: Decrypted file contents to inject
            
        Returns:
            Rendered prompt with data replacing {{data}} placeholder
            
        Note:
            If prompt template lacks {{data}}, it's automatically appended.
            Data is truncated with warning message if exceeding limits.
            Empty data injected if prompt itself exceeds limit.
        """
        prompt_template = grant_file.parameters.get("prompt", "")
        
        # Ensure {{data}} is in the prompt template
        if "{{data}}" not in prompt_template:
            logger.info("No {{data}} placeholder found in prompt, appending it to the end")
            prompt_template = prompt_template + "\n\n{{data}}"
        
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

