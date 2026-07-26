import os
import sys

# Ensure the backend directory is in the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.main import app
from mangum import Mangum

# Lambda handler mapped to Mangum adapter.
# text_mime_types is overridden to an empty tuple so Mangum treats ALL responses
# as potentially binary and always base64-encodes non-text bodies.
# API Gateway decodes base64 for binary_media_types (application/pdf, image/*).
lambda_handler = Mangum(app, lifespan="off", text_mime_types=())
