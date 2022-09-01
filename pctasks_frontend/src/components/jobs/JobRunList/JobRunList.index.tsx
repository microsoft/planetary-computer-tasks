import { mergeStyleSets, Stack } from "@fluentui/react";
import { hasSubJobs, isJobRun, isSubJobRun } from "helpers/jobs";
import { JobApiDefinition, JobRun } from "types";
import { JobRunWithSubJobs } from "components/jobs/JobRunWithSubJobs/JobRunWithSubJobs.index";
import { JobRunWithTasks } from "components/jobs/JobRunWithTasks/JobRunWithTasks.index";

interface JobRunListProps {
  jobs: JobApiDefinition[];
  runs: JobRun[] | undefined;
}

export const JobRunList: React.FC<JobRunListProps> = ({ jobs, runs }) => {
  const jobItems = jobs.map(job => {
    if (hasSubJobs(job)) {
      const subJobRuns = runs?.filter(isSubJobRun(job.id)) || [];
      return <JobRunWithSubJobs key={job.id} job={job} jobRuns={subJobRuns} />;
    }

    const jobRun = runs?.find(isJobRun(job.id));
    return (
      <div key={job.id}>
        <JobRunWithTasks
          key={job.id}
          job={job}
          jobRun={jobRun}
          initialTaskRuns={[]}
          indent={0}
        />
      </div>
    );
  });

  return <Stack className={styles.list}>{jobItems}</Stack>;
};

const styles = mergeStyleSets({
  list: {
    flexGrow: 1,
  },
});
