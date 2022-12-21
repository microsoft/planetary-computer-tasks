import { FontSizes, Link, mergeStyles, TooltipHost } from "@fluentui/react";
import { useCallback } from "react";
import { WorkflowRunRecord } from "types/runs";

interface WorkflowRunItemErrorsProps {
  run: WorkflowRunRecord;
}

export const WorkflowRunItemErrors: React.FC<WorkflowRunItemErrorsProps> = ({
  run,
}) => {
  const handleClick = useCallback(() => {
    console.log("TODO: navigate to error jobs for run", run.run_id);
  }, [run]);

  const errors = run.errors || [];
  const errorCountLabel = `${errors.length} error${errors.length === 1 ? "" : "s"}`;
  const errorsFormatted = (
    <ul>
      {errors.map((error, idx) => (
        <li key={`${run.run_id}-error-${idx}`}>{error}</li>
      ))}
    </ul>
  );

  return (
    <TooltipHost content={errorsFormatted}>
      <Link className={listSummaryStyles} onClick={handleClick}>
        {errorCountLabel}
      </Link>
    </TooltipHost>
  );
};

const listSummaryStyles = mergeStyles({
  fontSize: FontSizes.small,
});
