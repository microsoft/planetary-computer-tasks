import {
  Dropdown,
  getTheme,
  IDropdownStyles,
  mergeStyleSets,
  IDropdownOption,
} from "@fluentui/react";
import { ArrowCircleDownSplit20Regular } from "@fluentui/react-icons";

import { JobRun } from "types";
import { getSubJobStatusSummary } from "helpers/jobs";

interface JobStatusFilterProps {
  jobRuns: JobRun[];
  statusFilters: string[];
  onFilterChange: (filters: string[]) => void;
}

export const JobStatusFilter: React.FC<JobStatusFilterProps> = ({
  jobRuns,
  statusFilters,
  onFilterChange,
}) => {
  const jobSummary = getSubJobStatusSummary(jobRuns);
  const options = Object.entries(jobSummary)
    .filter(([, count]) => count > 0)
    .map(([status, count]): IDropdownOption => {
      return {
        key: status,
        text: `${status} (${count})`,
      };
    });

  const handleChange = (
    _: React.FormEvent<HTMLDivElement>,
    option?: IDropdownOption
  ) => {
    if (!option) return;
    const status = option.key as string;
    const newFilters = option.selected
      ? [...statusFilters, status]
      : statusFilters.filter(s => s !== status);

    onFilterChange(newFilters);
  };

  return (
    <Dropdown
      multiSelect
      title="This job has multiple run iterators. Click to filter."
      selectedKeys={statusFilters}
      styles={dropdownStyles}
      onRenderPlaceholder={() => (
        <ArrowCircleDownSplit20Regular className={styles.splits} />
      )}
      onRenderTitle={() => (
        <ArrowCircleDownSplit20Regular className={styles.splits} />
      )}
      options={options}
      onChange={handleChange}
      calloutProps={{
        isBeakVisible: true,
      }}
    />
  );
};

const theme = getTheme();
const styles = mergeStyleSets({
  splits: {
    color: theme.palette.neutralSecondary,
    marginTop: 3,
    width: 16,
    height: 16,
    "&:hover": {
      color: theme.semanticColors.link,
    },
  },
});

const dropdownStyles: Partial<IDropdownStyles> = {
  title: {
    i: {
      width: 14,
      height: 14,
      marginRight: 6,
      top: 4,
    },
    border: 0,
    padding: 0,
    lineHeight: "unset",
    display: "inline",
  },
  dropdownItemSelected: {
    backgroundColor: theme.palette.white,
  },
  caretDownWrapper: {
    display: "none",
  },
  dropdown: {
    "&:focus:after": {
      border: "0px ",
    },
    "&:focus-visible": {
      outline: "1px solid",
      outlineColor: theme.palette.neutralSecondary,
      borderRadius: 2,
    },
  },
  callout: {
    minWidth: 200,
  },
};
