import { WorkflowRecord } from "types/workflows";
import workflow from "./workflow.json";

// @ts-ignore -- test data file enums as string don't satisfy type checker
export const TestWorkflow: WorkflowRecord = workflow;
