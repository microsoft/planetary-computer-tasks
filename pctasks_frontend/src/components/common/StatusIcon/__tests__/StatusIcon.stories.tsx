import { ComponentStory, ComponentMeta } from "@storybook/react";

import WorkflowStatusIcon from "components/common/StatusIcon";
import { WorkflowRunStatus } from "types/enums";

export default {
  title: "PC Tasks/StatusIcon",
  component: WorkflowStatusIcon,
} as ComponentMeta<typeof WorkflowStatusIcon>;

const Template: ComponentStory<typeof WorkflowStatusIcon> = args => (
  <WorkflowStatusIcon {...args} />
);

export const Status = Template.bind({});
Status.args = {
  status: WorkflowRunStatus.completed,
};
