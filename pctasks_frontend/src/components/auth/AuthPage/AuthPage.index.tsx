import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import { IS_DEV } from "helpers/constants";
import React from "react";

export const AuthPage: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  if (IS_DEV) {
    return <>{children}</>;
  }

  return (
    <>
      <AuthenticatedTemplate>{children}</AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <div>You must be logged in to view this page.</div>
      </UnauthenticatedTemplate>
    </>
  );
};
