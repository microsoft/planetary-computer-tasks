import { ComponentStory, ComponentMeta } from "@storybook/react";
import { withRouter } from "storybook-addon-react-router-v6";

import { WorkflowRunItem } from "components/runs";
import { TestWorkflowRunItems } from "./data";

export default {
  title: "PC Tasks/WorkflowRunItem",
  component: WorkflowRunItem,
  decorators: [withRouter],
} as ComponentMeta<typeof WorkflowRunItem>;

const Template: ComponentStory<typeof WorkflowRunItem> = args => (
  <WorkflowRunItem {...args} />
);

export const Completed = Template.bind({});
Completed.args = {
  run: TestWorkflowRunItems.completed,
  selected: false,
};

export const Failed = Template.bind({});
Failed.args = {
  run: TestWorkflowRunItems.failed,
};

export const Running = Template.bind({});
Running.args = {
  run: TestWorkflowRunItems.running,
};

export const Submitted = Template.bind({});
Submitted.args = {
  run: TestWorkflowRunItems.submitted,
};
