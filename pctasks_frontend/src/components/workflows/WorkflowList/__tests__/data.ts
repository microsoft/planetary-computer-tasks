import { WorkflowRecord } from "types/workflows";
import workflows from "./workflows.json";

// @ts-ignore -- test data file enums as string don't satisfy type checker
export const TestWorkflows: WorkflowRecord[] = workflows;
