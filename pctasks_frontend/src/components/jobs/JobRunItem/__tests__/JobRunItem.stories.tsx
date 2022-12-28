// @ts-nocheck
import { ComponentStory, ComponentMeta } from "@storybook/react";
import { withRouter } from "storybook-addon-react-router-v6";

import { JobRunItem } from "components/jobs";
import { TestJobDefinitions, TestJobRuns } from "./data";

export default {
  title: "PC Tasks/ Runs /JobRunItem",
  component: JobRunItem,
  decorators: [withRouter],
} as ComponentMeta<typeof JobRunItem>;

const Template: ComponentStory<typeof JobRunItem> = args => <JobRunItem {...args} />;

export const BasicRun = Template.bind({});
BasicRun.args = {
  job: TestJobDefinitions,
  jobRuns: TestJobRuns,
};
