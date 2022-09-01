import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import { FontSizes, mergeStyles, Stack, Text } from "@fluentui/react";
import { IS_DEV } from "helpers/constants";
import { gapRegular, gapSmall } from "styles/global";
import { PcPersona } from "./PcPersona";
import { SignInButton } from "./SignInButton";

export const UserHeaderControl: React.FC = () => {
  const devMsg = IS_DEV ? (
    <Text
      block
      className={devModeStyle}
      title="Auth tokens are not retrieved when in dev mode, but you can still sign in if configured."
    >
      (dev mode)
    </Text>
  ) : null;

  return (
    <Stack tokens={gapSmall} verticalAlign="center">
      <Stack horizontal tokens={gapRegular}>
        <AuthenticatedTemplate>
          <PcPersona />
        </AuthenticatedTemplate>
        <UnauthenticatedTemplate>
          <SignInButton />
        </UnauthenticatedTemplate>
      </Stack>
      {devMsg}
    </Stack>
  );
};

const devModeStyle = mergeStyles({
  textAlign: "center",
  fontSize: FontSizes.small,
});
