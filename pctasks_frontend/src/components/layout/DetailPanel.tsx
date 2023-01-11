import { mergeStyleSets } from "@fluentui/react";

interface DetailPanelProps {
  children: React.ReactNode;
}

export const DetailPanel = ({ children }: DetailPanelProps) => {
  return <div className={styles.panel}>{children}</div>;
};

const styles = mergeStyleSets({
  panel: {
    display: "flex",
    flexDirection: "column",
    flexGrow: 2,
    width: "100%",
  },
});
