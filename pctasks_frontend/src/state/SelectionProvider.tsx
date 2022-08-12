import React, { createContext } from "react";
import { JobRun, TaskRun } from "types";

export interface SelectionProviderContext {
  selectedJobRun: JobRun | undefined;
  setSelectedJobRun: (jobRun: JobRun | undefined) => void;
  selectedTaskRun: TaskRun | undefined;
  setSelectedTaskRun: (taskRun: TaskRun | undefined) => void;
}

const initialState: SelectionProviderContext = {
  selectedJobRun: undefined,
  setSelectedJobRun: () => {},
  selectedTaskRun: undefined,
  setSelectedTaskRun: () => {},
};

const SelectionContext = createContext<SelectionProviderContext>(initialState);

interface Props {
  children: React.ReactNode;
}

export const SelectionProvider: React.FC<Props> = ({ children }) => {
  const [selectedJobRun, setSelectedJobRun] = React.useState<JobRun | undefined>();
  const [selectedTaskRun, setSelectedTaskRun] =
    React.useState<TaskRun | undefined>();

  const context: SelectionProviderContext = {
    selectedJobRun,
    setSelectedJobRun,
    selectedTaskRun,
    setSelectedTaskRun,
  };

  return (
    <SelectionContext.Provider value={context}>{children}</SelectionContext.Provider>
  );
};

export const useSelection = () => {
  const context = React.useContext(SelectionContext);
  if (context === undefined) {
    throw new Error("useSelection must be used within a SelectionProvider");
  }
  return context;
};
