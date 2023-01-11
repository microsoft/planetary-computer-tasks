import { IndentLevel } from "types";
import { JobParitionRunRecord, JobRunRecord } from "types/runs";
import { JobDefinition } from "types/jobs";
import { RunItem } from "components/common/RunItem/RunItem.index";
import { hasMultiplePartitions } from "helpers/jobs";

interface JobRunItemProps {
  job: JobDefinition;
  run: JobRunRecord | undefined;
  partitionRun?: JobParitionRunRecord;
  indent: IndentLevel;
  children?: React.ReactNode;
}

export const JobRunItem: React.FC<JobRunItemProps> = ({
  job,
  run,
  partitionRun,
  indent,
  children,
}) => {
  const titlePartitionId =
    partitionRun && hasMultiplePartitions(job)
      ? `[${partitionRun?.partition_id}]`
      : "";
  const title = `${job.id} ${titlePartitionId}`;

  const href = partitionRun ? undefined : `job/${job.id}`;
  const runItem = partitionRun || run;

  return (
    <RunItem title={title} run={runItem} indent={indent} href={href}>
      {children}
    </RunItem>
  );
};
