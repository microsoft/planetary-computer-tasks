import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { msalConfig } from "helpers/auth";
import reportWebVitals from "./reportWebVitals";

import "./index.css";
import App from "./App";
import { Home, WorkflowDetail, Workflows } from "pages";
import { initializeIcons } from "@fluentui/react";
import { SelectionProvider } from "state/SelectionProvider";

initializeIcons();

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
const queryClient = new QueryClient();

const msalInstance = new PublicClientApplication(msalConfig);

root.render(
  <React.StrictMode>
    <MsalProvider instance={msalInstance}>
      <QueryClientProvider client={queryClient}>
        <SelectionProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<App />}>
                <Route index element={<Home />} />
                <Route path="workflows" element={<Workflows />} />
                <Route
                  path="workflows/:workflowRunId"
                  element={<WorkflowDetail />}
                />
              </Route>
            </Routes>
          </BrowserRouter>
        </SelectionProvider>
      </QueryClientProvider>
    </MsalProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
