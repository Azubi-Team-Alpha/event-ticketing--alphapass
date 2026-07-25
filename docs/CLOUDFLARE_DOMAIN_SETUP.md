# Cloudflare Domain Setup & "NoSuchBucket" Troubleshooting Guide

This guide explains how to connect your domain (e.g. `alphapass.alphateam.live`) on Cloudflare to your AWS S3 static website hosting bucket, and how to resolve the **`404 Not Found Code: NoSuchBucket`** error.

---

## 🚨 Why `NoSuchBucket` Happens & How AWS S3 Works

When a browser opens `http://alphapass.alphateam.live` or `https://alphapass.alphateam.live`, AWS S3 checks the HTTP `Host` header sent by the client.

If the HTTP `Host` header is `alphapass.alphateam.live`, S3 looks for an S3 bucket named **`alphapass.alphateam.live`**.
If your S3 bucket in AWS is named `alphapass-frontend-dev`, S3 cannot find a bucket called `alphapass.alphateam.live` and throws:
```text
404 Not Found
Code: NoSuchBucket
Message: The specified bucket does not exist
BucketName: alphapass.alphateam.live
```

---

## 🛠️ Solution 1: Enable Cloudflare Orange-Cloud Proxy 🧡 + Host Header Rewrite (Recommended — No S3 Re-creation)

If you want to keep your existing S3 bucket name (`alphapass-frontend-dev`):

### Step 1: Turn ON Orange-Cloud Proxy in Cloudflare DNS
1. Open **[Cloudflare Dashboard](https://dash.cloudflare.com/)** $\rightarrow$ **DNS** $\rightarrow$ **Records**.
2. Locate the `alphapass` CNAME record.
3. Toggle the **Proxy status** from **Grey Cloud (DNS only)** to **Orange Cloud (Proxied 🧡)**.

---

### Step 2: Add Cloudflare Host Header Rewrite Rule
1. In Cloudflare Dashboard, go to **Rules** $\rightarrow$ **Transform Rules** (or **Origin Rules**).
2. Click **Create Rule** $\rightarrow$ **HTTP Request Header Modification**.
3. Fill in:
   - **Rule Name:** `S3 Host Header Rewrite`
   - **When incoming requests match:** `Hostname` equals `alphapass.alphateam.live`
   - **Modify request header:**
     - Action: **Set static**
     - Header Name: `Host`
     - Value: `alphapass-frontend-dev.s3-website-us-east-1.amazonaws.com` *(your S3 website bucket endpoint)*
4. Click **Deploy**.

*Now when clients request `https://alphapass.alphateam.live`, Cloudflare rewrite translates the Host header to `alphapass-frontend-dev.s3-website-us-east-1.amazonaws.com`. S3 serves your site with 0 errors!*

---

## 🛠️ Solution 2: Set Bucket Name to Match Domain Name Exactly in Terraform

AWS S3 allows direct CNAME pointing without host header rewrites if the S3 bucket name **matches the domain name exactly**: `alphapass.alphateam.live`.

### In Terraform:
Pass `custom_bucket_name = "alphapass.alphateam.live"` in `infra/terraform.tfvars`:
```hcl
environment        = "dev"
aws_region         = "us-east-1"
custom_bucket_name = "alphapass.alphateam.live"
```

Re-apply Terraform:
```bash
cd infra/
terraform apply -var="custom_bucket_name=alphapass.alphateam.live" -auto-approve
```

Then sync frontend files to the new bucket:
```bash
aws s3 sync ../frontend/ s3://alphapass.alphateam.live --delete
```

---

## 🎯 Verification

After configuring Solution 1 or Solution 2, clear your browser cache or run:
```bash
curl -I https://alphapass.alphateam.live
```
You will receive HTTP `200 OK` and your AlphaPass platform will render live!
