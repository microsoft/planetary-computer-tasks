import React, { createContext } from "react";
import { JobRunRecord, TaskRunRecord } from "types/runs";

export interface SelectionProviderContext {
  selectedJobRun: JobRunRecord | undefined;
  setSelectedJobRun: (jobRun: JobRunRecord | undefined) => void;
  selectedTaskRun: TaskRunRecord | undefined;
  setSelectedTaskRun: (taskRun: TaskRunRecord | undefined) => void;
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
  const [selectedJobRun, setSelectedJobRun] =
    React.useState<JobRunRecord | undefined>();
  const [selectedTaskRun, setSelectedTaskRun] =
    React.useState<TaskRunRecord | undefined>();

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
