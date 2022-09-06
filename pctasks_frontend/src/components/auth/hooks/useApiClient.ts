import axios, { AxiosInstance } from "axios";
import { useMsalToken } from "./useMsalToken";
import { API_ROOT } from "helpers/constants";

const getConfiguredClient = (accessToken: string): AxiosInstance => {
  const client = axios.create({
    baseURL: API_ROOT,
  });
  client.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`;
  return client;
};

export const useAuthApiClient = (): AxiosInstance | undefined => {
  const { accessToken } = useMsalToken();
  if (accessToken) {
    return getConfiguredClient(accessToken);
  }
  return undefined;
};
