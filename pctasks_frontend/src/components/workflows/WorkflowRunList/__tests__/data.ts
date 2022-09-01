import { WorkflowRun } from "types";
import longWorkflowRunsList from "./workflow-runs.json";
import { TestWorkflowRunItems } from "components/workflows/WorkflowRunItem/__tests__/data";

const { completed, failed, running, submitted } = TestWorkflowRunItems;
export const TestWorkflowRunListItems: WorkflowRun[] = [
  submitted,
  running,
  failed,
  completed,
];

// @ts-ignore -- test data file enums as string don't satisfy type checker
export const TestWorkflowRunListItemsLong: WorkflowRun[] = longWorkflowRunsList;
