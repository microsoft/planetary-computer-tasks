import React, { useEffect } from "react";
import {
  InteractionRequiredAuthError,
  InteractionStatus,
} from "@azure/msal-browser";
import { useMsal } from "@azure/msal-react";

import { tokenRequest } from "helpers/auth";
import { DEV_AUTH_TOKEN, IS_DEV } from "helpers/constants";

interface MsalTokenHookPropsReturn {
  accessToken: string | undefined;
  inProgress: InteractionStatus;
}

export const useMsalToken = (): MsalTokenHookPropsReturn => {
  const { instance, accounts, inProgress } = useMsal();
  const [accessToken, setAccessToken] = React.useState(
    IS_DEV ? DEV_AUTH_TOKEN : undefined
  );
  const account = accounts[0];

  const accessTokenRequest = {
    ...tokenRequest,
    account,
  };

  useEffect(() => {
    if (!accessToken && inProgress === InteractionStatus.None && account) {
      instance
        .acquireTokenSilent(accessTokenRequest)
        .then(accessTokenResponse => {
          setAccessToken(accessTokenResponse.accessToken);
        })
        .catch(error => {
          if (error instanceof InteractionRequiredAuthError) {
            instance
              .acquireTokenPopup(accessTokenRequest)
              .then(accessTokenResponse => {
                setAccessToken(accessTokenResponse.accessToken);
              })
              .catch(function (error) {
                console.error(error);
              });
          }
          console.warn(error);
        });
    }
  });

  return { accessToken, inProgress };
};
