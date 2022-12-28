import { mergeStyleSets, Stack } from "@fluentui/react";
import { isJobRun } from "helpers/jobs";
import { JobDefinition } from "types/jobs";
import { JobRunRecord } from "types/runs";
import { JobRunContainer } from "../JobRunContainer/JobRunContainer.index";

interface JobRunListProps {
  jobs: JobDefinition[] | undefined;
  runs: JobRunRecord[] | undefined;
}

export const JobRunList: React.FC<JobRunListProps> = ({ jobs, runs }) => {
  const jobItems = jobs?.map(job => {
    const jobRun = runs?.find(isJobRun(job.id));
    if (!jobRun) return null;
    return (
      <div key={job.id}>
        <JobRunContainer key={`jc-${job.id}`} jobDefinition={job} jobRun={jobRun} />
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
