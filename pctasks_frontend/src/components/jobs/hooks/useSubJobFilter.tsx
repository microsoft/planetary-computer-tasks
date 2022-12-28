import { useState } from "react";
import { JobParitionRunRecord } from "types/runs";
import { JobPartitionRunStatus } from "types/enums";
import { JobPartitionFilter } from "../JobStatusFilter/JobStatusFilter.index";

export const useSubJobFilter = (jobPartitionRuns: JobParitionRunRecord[]) => {
  const [filter, setFilter] = useState<string[]>(allStatuses);

  const filterPanel = (
    <JobPartitionFilter
      jobPartitionRuns={jobPartitionRuns}
      onFilterChange={setFilter}
      statusFilters={filter}
    />
  );

  const filteredJobPartitionRuns = jobPartitionRuns.filter(run =>
    filter.includes(run.status)
  );

  return { filterPanel, filteredJobPartitionRuns };
};

const allStatuses = Object.values(JobPartitionRunStatus)
  .map(key => JobPartitionRunStatus[key])
  .filter(value => typeof value === "string") as string[];
