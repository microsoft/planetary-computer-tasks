import { ComponentStory, ComponentMeta } from "@storybook/react";
import { withRouter } from "storybook-addon-react-router-v6";

import { WorkflowRunList } from "components/runs";
import { TestWorkflowRunListItems, TestWorkflowRunListItemsLong } from "./data";

export default {
  title: "PC Tasks/WorkflowRunList",
  component: WorkflowRunList,
  decorators: [withRouter],
} as ComponentMeta<typeof WorkflowRunList>;

const Template: ComponentStory<typeof WorkflowRunList> = args => (
  <WorkflowRunList {...args} />
);

export const Basic = Template.bind({});
Basic.args = {
  runs: TestWorkflowRunListItems,
};

export const Long = Template.bind({});
Long.args = {
  runs: TestWorkflowRunListItemsLong,
};
