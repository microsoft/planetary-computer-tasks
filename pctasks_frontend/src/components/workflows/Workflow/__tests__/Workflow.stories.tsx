import { ComponentStory, ComponentMeta } from "@storybook/react";
import { withRouter } from "storybook-addon-react-router-v6";

import { TestWorkflow } from "./data";
import { Workflow } from "../Workflow.index";

export default {
  title: "PC Tasks / Workflow/ Item",
  component: Workflow,
  decorators: [withRouter],
} as ComponentMeta<typeof Workflow>;

const Template: ComponentStory<typeof Workflow> = args => <Workflow {...args} />;

export const Basic = Template.bind({});
Basic.args = {
  workflow: TestWorkflow,
};

// export const Long = Template.bind({});
// Long.args = {
//   runs: TestWorkflowRunListItemsLong,
// };
