import { JobDefinition } from "types/jobs";
import { JobRunRecord } from "types/runs";

export const hasMultiplePartitions = (job: JobDefinition): boolean => {
  return Boolean(job.foreach);
};

export const isJobRun = (jobId: string): ((run: JobRunRecord) => boolean) => {
  return (run: JobRunRecord): boolean => {
    return jobId === run.job_id;
  };
};
