import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import { Stack } from "@fluentui/react";
import { gapRegular } from "styles/global";
import { PcPersona } from "./PcPersona";
import { SignInButton } from "./SignInButton";

export const UserHeaderControl: React.FC = () => {
  return (
    <Stack horizontal tokens={gapRegular}>
      <AuthenticatedTemplate>
        <PcPersona />
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <SignInButton />
      </UnauthenticatedTemplate>
    </Stack>
  );
};
