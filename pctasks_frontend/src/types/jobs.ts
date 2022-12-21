import { ItemNotificationConfig, TaskDefinition } from "types";

export type JobDefinition = {
  id: string;
  tasks: TaskDefinition[];
  foreach: [];
  notifications: ItemNotificationConfig[] | null;
  needs: string | string[] | null;
};
