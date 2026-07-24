import uuid
import boto3
from app.core.config import settings


def upload_image_to_s3(image_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    """Upload arbitrary image bytes to S3 and return public URL or fallback path."""
    ext = filename.split(".")[-1] if "." in filename else "jpg"
    key = f"events/banners/{uuid.uuid4().hex}.{ext}"

    if not settings.S3_BUCKET_NAME:
        return "/banners/demo.png"

    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=image_bytes,
            ContentType=content_type
        )
        region = settings.AWS_REGION
        return f"https://{settings.S3_BUCKET_NAME}.s3.{region}.amazonaws.com/{key}"
    except Exception as e:
        print(f"[S3] Upload failed for {key}: {e}")
        return "/banners/demo.png"
