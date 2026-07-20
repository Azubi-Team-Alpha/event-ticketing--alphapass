import qrcode
import io
import boto3
from app.core.config import settings


def generate_qr_code(ticket_code: str) -> bytes:
    """Generate a QR code image as bytes for a given ticket code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # type: ignore
        box_size=10,
        border=4,
    )
    qr.add_data(ticket_code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")  # type: ignore
    buffer.seek(0)
    return buffer.getvalue()


def upload_qr_to_s3(ticket_code: str) -> str:
    """
    Generates a QR code and uploads it to S3.
    Returns the public URL of the uploaded image.
    """
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    key = f"tickets/qr/{ticket_code}.png"
    image_bytes = generate_qr_code(ticket_code)

    s3.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=image_bytes,
        ContentType="image/png",
    )

    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
