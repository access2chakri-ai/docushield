"""
Early configuration module for AWS App Runner deployment
Fans out DOCUSHIELD_CONFIG_JSON secret to individual environment variables

SAFE FOR LOCAL DEVELOPMENT:
- Only processes DOCUSHIELD_CONFIG_JSON if it exists
- Does not override existing environment variables
- Falls back to .env file or other env vars if JSON secret is not present
"""
import os
import json
import logging

def fan_out_json_secret(env_name="DOCUSHIELD_CONFIG_JSON"):
    """
    Parse the JSON secret and set individual environment variables
    
    Args:
        env_name: The name of the environment variable containing the JSON secret
    """
    raw = os.getenv(env_name)
    if not raw:
        # No JSON secret found - this is normal for local development
        # The app will use .env file or other environment variables
        return
    
    try:
        # Parse the JSON secret
        data = json.loads(raw)
        
        # Set each key-value pair as an environment variable
        # Only set if the environment variable doesn't already exist
        for key, value in data.items():
            if key not in os.environ:
                os.environ[key] = str(value)
        
        # Log the configuration source for debugging
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 Configuration: Loaded {len(data)} variables from {env_name}")
        
    except json.JSONDecodeError as e:
        # Log error but don't fail startup
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Failed to parse {env_name}: {e}")
    except Exception as e:
        # Log any other error but don't fail startup
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Error processing {env_name}: {e}")

# Automatically fan out the JSON secret when this module is imported
fan_out_json_secret()