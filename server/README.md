# Personal Server

Personal server for data portability. 

## Deploy to Replicate

### Prerequisites
- Replicate account and API token
- Python 3.8+ installed locally

### Steps

1. **Install Replicate CLI**
   ```bash
   pip install replicate
   ```

2. **Login to Replicate**
   ```bash
   replicate login
   ```

3. **Create a replicate.yaml configuration file**
   ```yaml
   build:
     gpu: false
     python_version: "3.8"
     system_packages:
       - "build-essential"
   predict: predict.py:Predictor
   ```

4. **Deploy the model**
   ```bash
   replicate deploy
   ```

5. **Test the deployment**
   ```bash
   replicate predict --input signature="your_signature" request_json="your_request_json"
   ```

### Environment Variables
Make sure to set the following environment variables in your Replicate deployment:
- `REPLICATE_AUTH_TOKEN`: Your Replicate API token
- Any other required environment variables from your `.env` file

### Notes
- The `predict.py` file contains the `Predictor` class that Replicate will use to run predictions
- The deployment uses the existing `PersonalServer` and `Llm` classes from your codebase
- GPU is disabled by default but can be enabled if needed for your LLM operations
