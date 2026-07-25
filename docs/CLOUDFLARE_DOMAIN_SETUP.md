# Cloudflare Domain Setup Guide for AlphaPass

This guide explains how your custom domain **`alphapass.alphateam.live`** connects seamlessly to your AWS S3 static website hosting bucket using Cloudflare free DNS proxy SSL.

---

## 🎯 Architecture Overview

- **Custom Domain:** `https://alphapass.alphateam.live`
- **AWS S3 Bucket Name:** `alphapass.alphateam.live` *(Matches domain name 1:1 for direct AWS CNAME resolution)*
- **S3 Endpoint:** `alphapass.alphateam.live.s3-website-us-east-1.amazonaws.com`
- **Cloudflare DNS Record:** `CNAME alphapass -> alphapass.alphateam.live.s3-website-us-east-1.amazonaws.com`
- **Proxy Status:** **Proxied (Orange Cloud 🧡)**

---

## 📋 Cloudflare DNS Configuration Steps

1. Log into **[Cloudflare Dashboard](https://dash.cloudflare.com/)** and select domain `alphateam.live`.
2. Go to **DNS** $\rightarrow$ **Records** $\rightarrow$ Click **Add Record**.
3. Fill in the CNAME record details:

| Field | Value | Description |
|---|---|---|
| **Type** | `CNAME` | Canonical Name record |
| **Name** | `alphapass` | Subdomain name (`alphapass.alphateam.live`) |
| **Target** | `alphapass.alphateam.live.s3-website-us-east-1.amazonaws.com` | S3 website endpoint |
| **Proxy status** | **Proxied** (Orange Cloud 🧡) | Enables free HTTPS/SSL termination & DDoS protection |
| **TTL** | `Auto` | Default automatic TTL |

---

## 🔒 SSL/TLS Edge Settings

1. In Cloudflare Dashboard, navigate to **SSL/TLS** $\rightarrow$ **Overview**.
2. Set Encryption Mode to **Flexible** (or **Full**).
3. Under **SSL/TLS** $\rightarrow$ **Edge Certificates**, set **Always Use HTTPS** to **ON**.

---

## 🚀 Deployment Verification

```bash
# Test DNS CNAME resolution
dig alphapass.alphateam.live CNAME

# Test HTTPS connection
curl -I https://alphapass.alphateam.live
```

Output:
```text
HTTP/2 200
server: cloudflare
content-type: text/html
```

Your AlphaPass static web application is live, secure, and globally cached at **`https://alphapass.alphateam.live`**!
