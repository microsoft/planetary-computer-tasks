import {
  getTheme,
  Label,
  mergeStyles,
  mergeStyleSets,
  Stack,
  Text,
} from "@fluentui/react";
import { borderRound } from "styles/global";
import { JobRunRecord } from "types/runs";

interface JobRunErrorsProps {
  run: JobRunRecord | undefined;
}

export const JobRunErrors = ({ run }: JobRunErrorsProps) => {
  const errors = run?.errors?.map((error, idx) => {
    const key = `${run.job_id}-${idx}`;
    return (
      <code className={styles.errorItem} key={key}>
        {error}
      </code>
    );
  });

  const noErrors = <Text>No errors were logged for this job run.</Text>;

  return (
    <>
      <h4>Job Run Errors</h4>
      {run?.errors ? errors : noErrors}
    </>
  );
};

const theme = getTheme();
const styles = mergeStyleSets({
  errorItem: mergeStyles(borderRound, {
    margin: 4,
    padding: 4,
  }),
});
// const;
