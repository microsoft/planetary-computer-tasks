import { ComponentStory, ComponentMeta } from "@storybook/react";

import { JobRunPartitionWithTasks } from "../JobRunWithTasks.index";
import {
  TestJobDefinitions,
  TestJobRuns,
} from "components/jobs/JobRunItem/__tests__/data";
import { TestTaskRuns } from "components/tasks/TaskRunItem/__tests__/data";
import { TestTaskRuns as chunkTaskRuns } from "components/tasks/TaskRunList/__tests__/data";

export default {
  title: "PC Tasks/JobRunWithTasks",
  component: JobRunPartitionWithTasks,
} as ComponentMeta<typeof JobRunPartitionWithTasks>;

const Template: ComponentStory<typeof JobRunPartitionWithTasks> = args => (
  <JobRunPartitionWithTasks {...args} />
);

const splitsJobRuns = TestJobRuns.find(job => job.job_id === "create-splits");
export const Single = Template.bind({});
Single.args = {
  // @ts-ignore
  job: TestJobDefinitions["create-splits"],
  // @ts-ignore
  jobRun: splitsJobRuns,
  // @ts-ignore
  initialTaskRuns: [TestTaskRuns["create-splits"]],
};

const chunkJobRun = TestJobRuns.find(job => job.job_id === "process-chunk[0]");
if (chunkJobRun) chunkJobRun.job_id = "process-chunk";
export const Multiple = Template.bind({});
Multiple.args = {
  // @ts-ignore
  job: TestJobDefinitions["process-chunk"],
  // @ts-ignore
  jobRun: chunkJobRun,
  // @ts-ignore
  initialTaskRuns: chunkTaskRuns["process-chunk"],
};
