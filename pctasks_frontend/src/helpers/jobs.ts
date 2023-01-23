import { JobApiDefinition, JobRun } from "types";
import dayjs from "dayjs";
import { JobRunStatus } from "types/enums";

type JobRunStatusCounts = Record<JobRunStatus, number>;

export const hasSubJobs = (job: JobApiDefinition): boolean => {
  return Boolean(job.foreach);
};

export const isSubJobRun = (jobId: string): ((run: JobRun) => boolean) => {
  return (run: JobRun): boolean => {
    // If the regex matches jobId[number], then it's a sub job
    const re = new RegExp(`^${jobId}[[0-9]+]$`);
    return re.test(run.job_id);
  };
};

export const isJobRun = (jobId: string): ((run: JobRun) => boolean) => {
  return (run: JobRun): boolean => {
    return jobId === run.job_id;
  };
};

export const makeSyntheticJobRun = (
  job_id: string,
  runs: JobRun[]
): JobRun | undefined => {
  // Jobs may not have any runs, if they failed prior to start.
  if (!runs.length) return undefined;

  // Find the job run with the earliest created time
  const earliestRun = runs.reduce((earliest, current): JobRun => {
    if (dayjs(earliest.created).isBefore(dayjs(current.created))) {
      return earliest;
    }
    return current;
  }, runs[0]);

  // Find the job run with the latest created time
  const latestRun = runs.reduce((latest, current) => {
    if (dayjs(latest.updated).isAfter(dayjs(current.updated))) {
      return latest;
    }
    return current;
  }, runs[0]);

  const synthStatus = getSynthStatus(runs);

  return {
    created: earliestRun.created,
    updated: latestRun.updated,
    status: synthStatus,
    errors: [],
    run_id: runs[0].run_id,
    job_id: job_id,
    links: null,
  };
};

export const getSubJobStatusSummary = (runs: JobRun[]): JobRunStatusCounts => {
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

const getSynthStatus = (runs: JobRun[]): JobRunStatus => {
  // Determine the synthetic job run's status. If all jobs have a completed
  // status, then the job run is completed.  If any are failed, then the job run
  // is failed. If the completed count is less than the total count, then the
  // job run is in progress.
  const statuses = getSubJobStatusSummary(runs);

  // All completed
  if (statuses.completed === runs.length) {
    return JobRunStatus.completed;
  }

  // Any failed
  if (statuses.failed > 0) {
    return JobRunStatus.failed;
  }

  // Any are running, but none have failed
  if (statuses.running > 0) {
    return JobRunStatus.running;
  }

  // Any are pending, but none have failed or are running
  if (statuses.pending > 0) {
    return JobRunStatus.pending;
  }

  // Any are notasks, but none have failed or are running or are pending
  if (statuses.notasks > 0) {
    return JobRunStatus.notasks;
  }

  return JobRunStatus.cancelled;
};
