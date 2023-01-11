import { Label, Stack, Text } from "@fluentui/react";
import { gapRegular } from "styles/global";
import { JobDefinition } from "types/jobs";

interface JobDefinitionProps {
  jobDefinition: JobDefinition | undefined;
}

export const JobDefinitionDetail = ({ jobDefinition }: JobDefinitionProps) => {
  return (
    <>
      <h4>Job Definition Detail</h4>
      <Stack horizontal wrap tokens={gapRegular}>
        <div>
          <Label>Job ID</Label>
          {jobDefinition?.id || "-"}
        </div>
      </Stack>
    </>
  );
};

// const;
