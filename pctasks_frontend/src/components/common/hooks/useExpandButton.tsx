import { getTheme, IconButton, mergeStyleSets } from "@fluentui/react";
import { ChevronDown20Filled, ChevronRight20Filled } from "@fluentui/react-icons";
import { useState } from "react";

export const useExpandButton = (defaultExpanded: boolean) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const chevron = isExpanded ? (
    <ChevronDown20Filled className={styles.icon} />
  ) : (
    <ChevronRight20Filled className={styles.icon} />
  );
  const title = isExpanded ? "Collapse" : "Expand";
  const toggleButton = (
    <IconButton
      title={`${title} children`}
      onRenderIcon={() => chevron}
      onClick={() => setIsExpanded(!isExpanded)}
    />
  );

  return { isExpanded, setIsExpanded, toggleButton };
};

const theme = getTheme();
const styles = mergeStyleSets({
  icon: {
    color: theme.semanticColors.bodyText,
  },
});
