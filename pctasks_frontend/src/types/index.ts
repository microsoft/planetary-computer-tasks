import { LinkRel } from "./enums";

export type ResponseLink = {
  rel: LinkRel;
  href: string;
  type?: string;
  title?: string;
};

export type PCTRecord = {
  type: string;
  schema_version: string;
  created: string;
  updated: string;
  deleted: boolean;
};

export type TaskDefinition = {
  id: string;
  image: string | null;
  image_key: string | null;
  code: CodeConfig | null;
  task: string;
  args: Record<string, any>;
  tags: Record<string, string> | null;
  environment: Record<string, string> | null;
};

export type ForeachConfig = {
  items: string | any[] | null;
  flatten: boolean;
};

// TODO
export type ItemNotificationConfig = any;
export type CodeConfig = any;
export type TriggerConfig = any;
export type StorageAccountTokens = any;
export type DatasetIdentifier = any;

export type CloudEvent = {
  spec_version: string;
  type: string;
  source: string;
  subject?: string;
  id: string;
  time: string;
  data_content_type: string;
  data: Record<string, any>;
};

export type IndentLevel = number;
