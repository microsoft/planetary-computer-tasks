import { ComponentStory, ComponentMeta } from "@storybook/react";
import TaskRunItem from "components/tasks/TaskRunItem";
import { TestTaskDefinitions, TestTaskRuns } from "./data";

export default {
  title: "PC Tasks/TaskRunItem",
  component: TaskRunItem,
} as ComponentMeta<typeof TaskRunItem>;

const Template: ComponentStory<typeof TaskRunItem> = args => (
  <TaskRunItem {...args} />
);

export const Single = Template.bind({});
Single.args = {
  task: TestTaskDefinitions["create-splits"],
  // @ts-ignore
  taskRun: TestTaskRuns["create-splits"],
};
