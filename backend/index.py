import os
import sys

# Ensure the backend directory is in the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.main import app
from mangum import Mangum

# Lambda handler mapped to Mangum adapter
lambda_handler = Mangum(app, lifespan="off")
