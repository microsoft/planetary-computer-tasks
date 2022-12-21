import { ComponentStory, ComponentMeta } from "@storybook/react";
import { withRouter } from "storybook-addon-react-router-v6";

import { WorkflowList } from "components/workflows";
import { TestWorkflows } from "./data";

export default {
  title: "PC Tasks / Workflow / List",
  component: WorkflowList,
  decorators: [withRouter],
} as ComponentMeta<typeof WorkflowList>;

const Template: ComponentStory<typeof WorkflowList> = args => (
  <WorkflowList {...args} />
);

export const Basic = Template.bind({});
Basic.args = {
  workflows: TestWorkflows,
};
