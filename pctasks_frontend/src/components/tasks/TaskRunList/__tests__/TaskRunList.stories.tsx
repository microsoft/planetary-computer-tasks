import { ComponentStory, ComponentMeta } from "@storybook/react";
import TaskRunList from "components/tasks/TaskRunList";
import { TestJobTasks, TestTaskRuns } from "./data";

export default {
  title: "PC Tasks/TaskRunList",
  component: TaskRunList,
} as ComponentMeta<typeof TaskRunList>;

const Template: ComponentStory<typeof TaskRunList> = args => (
  <TaskRunList {...args} />
);

export const Basic = Template.bind({});
Basic.args = {
  tasks: TestJobTasks["process-chunk"],
  // @ts-ignore
  taskRuns: TestTaskRuns["process-chunk"],
};
