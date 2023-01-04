import { useJobRunPartition } from "helpers/api";
import { JobDefinition } from "types/jobs";
import { JobRunRecord } from "types/runs";
import { JobRunWithPartitions } from "../JobRunWithPartitions/JobRunWithPartitions.index";
import { JobRunPartitionWithTasks } from "../JobRunWithTasks/JobRunWithTasks.index";

interface JobRunContainerProps {
  jobDefinition: JobDefinition;
  jobRun: JobRunRecord;
}

export const JobRunContainer: React.FC<JobRunContainerProps> = ({
  jobDefinition,
  jobRun,
}) => {
  const { data: jobRunPartitions } = useJobRunPartition(jobRun);

  if (!jobRunPartitions) return null;

  if (jobRunPartitions.length > 1) {
    return (
      <JobRunWithPartitions
        job={jobDefinition}
        jobRun={jobRun}
        jobRunPartitions={jobRunPartitions}
      />
    );
  }

  return (
    <JobRunPartitionWithTasks
      job={jobDefinition}
      jobRun={jobRun}
      jobRunPartition={jobRunPartitions[0]}
      indent={0}
    />
  );
};
