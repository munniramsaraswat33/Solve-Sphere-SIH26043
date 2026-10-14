# Authentication setup

## Google sign-in configuration

Google sign-in uses Google Identity Services in the browser to return an ID
token. The API verifies the token signature using Google's rotating public
signing keys, then validates its expiry, issuer, audience, and verified email
before it creates or retrieves a user and issues a Solve Sphere session. The
Google identity token is never trusted based on browser-provided email/name
fields alone.

### 1. Create a Google OAuth web client

1. Open [Google Cloud Console](https://console.cloud.google.com/). Use the
   project picker at the top to select a project, or choose **New project**,
   give it a name, and create it.
2. Open **Google Auth Platform**. If prompted, choose **Get started**.
3. On **Branding**, provide the app name and a support email, then save. Add an
   authorized domain only if you own and use a public domain; localhost is not
   an authorized domain requirement.
4. On **Audience**, choose **External** for regular Google/Gmail accounts.
   Choose **Internal** only if the app should be limited to users in your
   Google Workspace organization. While an External app is in **Testing**, add
   each Google account that should be allowed to sign in under **Test users**.
5. Open **Clients** and choose **Create client**. Select **Web application**,
   give it a name such as `Solve Sphere local`, then create it.
6. In **Authorized JavaScript origins**, add these local development origins:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
7. For a deployed app, add the exact frontend origin (for example,
   `https://app.example.com`) as another authorized JavaScript origin.

This project uses the Google Identity Services JavaScript popup callback, not a
redirect-based flow. No **Authorized redirect URI** is required for this
implementation. If the Google Cloud Console shows a client secret, this popup
flow does not use it: keep it private and do not put it in either project env
file. The OAuth **Client ID** is the only Google credential this flow needs.

### 2. Configure local environment files

In two PowerShell terminals opened at the project root, copy the templates:

```powershell
Copy-Item frontend\.env.example frontend\.env
Copy-Item backend\.env.example backend\.env
code frontend\.env
code backend\.env
```

Copy the **Web client ID** shown for the new client (it ends in
`.apps.googleusercontent.com`) into both files. Do not copy a client secret:

```dotenv
# frontend/.env
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

```dotenv
# backend/.env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

The client ID is a public identifier and is intentionally used by the browser;
it is not a client secret. Do not create or add a client secret to either file
for this flow. Never put private credentials in a `VITE_` variable. Local `.env`
files are ignored by Git; keep them out of commits.

The API also needs `JWT_SECRET_KEY` (at least 32 characters) and working
MongoDB settings in `backend/.env` to create accounts and issue sessions. Set
those values in the backend environment; do not use the example's blank JWT
value in a running deployment. Local `.env` files are ignored by Git.

### 3. Install and run

From the project root, install the backend dependencies and start the API:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Restart both servers after changing environment values; Vite reads its `VITE_`
variables at startup. If Google configuration is missing, the button reports
which env values to set and the API returns a configuration error rather than
crashing. Email/password registration and login remain available without Google
configuration.
