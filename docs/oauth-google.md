# Google OAuth Setup

Use a Google OAuth 2.0 Web application client. The **GOOGLE_CLIENT_ID** is the
OAuth client ID (not the project ID) created in the Google Cloud Console.

## Create Credentials

1. Open the Google Cloud Console credentials page:
   https://console.cloud.google.com/apis/credentials
2. Create **OAuth client ID** → **Web application**
3. Set authorized origins and redirect URIs:
   - Authorized JavaScript origins: `http://localhost:3000`
   - Authorized redirect URIs: `http://localhost:8000/api/v1/oauth/google/callback`

## Configure Environment Variables

Add to the repo root `.env`:

```
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/oauth/google/callback
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Restart the backend and frontend after updating `.env`.

## Notes

- `GOOGLE_CLIENT_ID` must be the OAuth **client ID** from the Google Cloud Console.
- `GOOGLE_CLIENT_SECRET` is only used on the server.
- Update origins/redirects for staging/production domains.
