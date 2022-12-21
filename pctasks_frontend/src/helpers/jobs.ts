import { JobDefinition } from "types/jobs";
import { JobRunStatus } from "types/enums";
import { JobRunRecord } from "types/runs";

type JobRunStatusCounts = Record<JobRunStatus, number>;

export const hasSubJobs = (job: JobDefinition): boolean => {
  return Boolean(job.foreach);
};

export const isSubJobRun = (jobId: string): ((run: JobRunRecord) => boolean) => {
  return (run: JobRunRecord): boolean => {
    // If the regex matches jobId[number], then it's a sub job
    const re = new RegExp(`^${jobId}[[0-9]+]$`);
    return re.test(run.job_id);
  };
};

export const isJobRun = (jobId: string): ((run: JobRunRecord) => boolean) => {
  return (run: JobRunRecord): boolean => {
    return jobId === run.job_id;
  };
};

export const getSubJobStatusSummary = (runs: JobRunRecord[]): JobRunStatusCounts => {
  return runs.reduce<JobRunStatusCounts>(
    (statusCount: JobRunStatusCounts, current) => {
      statusCount[current.status]++;
      return statusCount;
    },
    {
      completed: 0,
      failed: 0,
      pending: 0,
      running: 0,
      notasks: 0,
      cancelled: 0,
    }
  );
};
