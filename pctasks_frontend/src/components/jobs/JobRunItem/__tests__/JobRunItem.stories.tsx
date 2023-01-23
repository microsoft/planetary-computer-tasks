// @ts-nocheck
import { ComponentStory, ComponentMeta } from "@storybook/react";
import { withRouter } from "storybook-addon-react-router-v6";

import JobRunItem from "components/jobs/JobRunItem";
import { TestJobDefinitions, TestJobRuns } from "./data";
import { isJobRun, isSubJobRun } from "helpers/jobs";

export default {
  title: "PC Tasks/JobRunItem",
  component: JobRunItem,
  decorators: [withRouter],
} as ComponentMeta<typeof JobRunItem>;

const Template: ComponentStory<typeof JobRunItem> = args => <JobRunItem {...args} />;

const splitsJob = TestJobRuns.filter(isJobRun("create-splits"));
const chunkJobs = TestJobRuns.filter(isSubJobRun("create-chunks"));
const processJobs = TestJobRuns.filter(isSubJobRun("process-chunk"));
const postProcessJobs = TestJobRuns.filter(isSubJobRun("post-process-chunk"));

export const NoSubJobs = Template.bind({});
NoSubJobs.args = {
  job: TestJobDefinitions["create-splits"],
  jobRuns: splitsJob,
};

export const WithSingleSubJob = Template.bind({});
WithSingleSubJob.args = {
  job: TestJobDefinitions["create-chunks"],
  jobRuns: chunkJobs,
};

export const WithCompletedSubJobs = Template.bind({});
WithCompletedSubJobs.args = {
  job: TestJobDefinitions["process-chunk"],
  jobRuns: processJobs,
};

export const WithCompletedAndFailedSub = Template.bind({});
WithCompletedAndFailedSub.args = {
  job: TestJobDefinitions["post-process-chunk"],
  jobRuns: postProcessJobs,
};
