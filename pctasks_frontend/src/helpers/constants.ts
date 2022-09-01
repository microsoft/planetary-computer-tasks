// By setting DEV mode, we expect to target a localhost environment and use a
// static Bearer token for API authentication.
window.publicConfig = process.env;
export const IS_DEV = process.env.REACT_APP_IS_DEV === "true";
export const DEV_AUTH_TOKEN = IS_DEV
  ? process.env.REACT_APP_DEV_AUTH_TOKEN
  : undefined;

/*
  Authenticated oAuth2 token request variables. These are not secret values, but
  vary by environment. These are unused environment when IS_DEV is true.
*/
export const AUTH_TENANT_ID = process.env.REACT_APP_AUTH_TENANT_ID || "";
export const AUTH_CLIENT_ID = process.env.REACT_APP_AUTH_CLIENT_ID || "";
export const AUTH_BACKEND_APP_ID = process.env.REACT_APP_AUTH_BACKEND_APP_ID || "";
export const API_READ_SCOPE = `api://${AUTH_BACKEND_APP_ID}/Runs.Read.All`;
export const API_WRITE_SCOPE = `api://${AUTH_BACKEND_APP_ID}/Runs.Write.All`;

// The API endpoint to use for authenticated API requests.
export const API_ROOT = process.env.REACT_APP_API_ROOT;

// Validate some settings and print appropriate warnings.
if (IS_DEV) {
  if (API_ROOT?.startsWith("http://localhost")) {
    console.warn(`Using development API URL: ${API_ROOT}`);
  } else {
    console.error(`Development API URL is not localhost: ${API_ROOT}`);
  }
} else {
  if (
    ![AUTH_TENANT_ID, AUTH_CLIENT_ID, AUTH_BACKEND_APP_ID, API_READ_SCOPE].every(
      Boolean
    )
  ) {
    console.error("Missing authentication app environment variables");
  }

  if (API_ROOT?.startsWith("http://localhost")) {
    console.warn(
      `Possible misconfiguration: using localhost in non-development mode.`
    );
  }
}
